using System.Collections.Immutable;
using System.Reflection;
using System.Reflection.Metadata;
using System.Reflection.PortableExecutable;
using System.Security.Cryptography;
using System.Text.Json;

namespace Thorkell.ApiCheck;

// 게임 DLL 메타데이터만 읽어서(게임 실행 없이) Thorkell이 쓰는 타입·멤버가 그대로 있는지 확인한다.
// RequiredApi.json에 적힌 멤버 하나라도 없거나 시그니처가 다르면 종료 코드 1.
public static class Program
{
    public static int Main(string[] args)
    {
        if (args.Length == 3 && args[0] == "--dump")
            return Dump(args[1], args[2]);

        var options = ParseArgs(args);
        var managed = Path.Combine(options["--game-root"], "Valheim.app/Contents/Resources/Data/Managed");
        var required = JsonDocument.Parse(File.ReadAllText(options["--required"])).RootElement;
        var tested = JsonDocument.Parse(File.ReadAllText(options["--tested"])).RootElement;

        var failures = 0;
        var assemblies = new Dictionary<string, Assembly>();
        foreach (var name in required.GetProperty("assemblies").EnumerateArray().Select(e => e.GetString()!))
            assemblies[name] = Assembly.Open(Path.Combine(managed, name));

        failures += CheckBuild(tested, assemblies);

        var checkedCount = 0;
        foreach (var entry in required.GetProperty("members").EnumerateArray())
        {
            checkedCount++;
            var problem = CheckMember(entry, assemblies);
            if (problem != null)
            {
                failures++;
                Console.WriteLine("MISSING " + Describe(entry) + " — " + problem + " (used by " + entry.GetProperty("used_by").GetString() + ")");
            }
        }

        Console.WriteLine(failures == 0
            ? "OK: " + checkedCount + " members present, build matches tested-versions.json"
            : "FAILED: " + failures + " problem(s)");
        return failures == 0 ? 0 : 1;
    }

    // 개발 보조: `--dump <dll 경로> <타입>`으로 필드·속성·메서드 시그니처를 출력한다.
    static int Dump(string dllPath, string typeName)
    {
        var assembly = Assembly.Open(dllPath);
        var type = assembly.FindType(typeName);
        if (type == null)
        {
            Console.WriteLine("type not found: " + typeName);
            return 1;
        }
        foreach (var line in assembly.Describe(type.Value))
            Console.WriteLine(line);
        return 0;
    }

    static Dictionary<string, string> ParseArgs(string[] args)
    {
        var result = new Dictionary<string, string>();
        for (int i = 0; i + 1 < args.Length; i += 2)
            result[args[i]] = args[i + 1];
        foreach (var key in new[] { "--game-root", "--required", "--tested" })
            if (!result.ContainsKey(key))
                throw new ArgumentException("missing " + key);
        return result;
    }

    static int CheckBuild(JsonElement tested, Dictionary<string, Assembly> assemblies)
    {
        var failures = 0;
        var builds = tested.GetProperty("builds").EnumerateArray().ToList();
        var hashes = assemblies.ToDictionary(a => a.Key, a => a.Value.Sha256);
        var match = builds.FirstOrDefault(b => b.GetProperty("sha256").EnumerateObject()
            .All(p => hashes.TryGetValue(p.Name, out var h) && h == p.Value.GetString()));
        if (match.ValueKind == JsonValueKind.Undefined)
        {
            Console.WriteLine("UNTESTED BUILD: assembly hashes match no entry in tested-versions.json");
            foreach (var pair in hashes)
                Console.WriteLine("  " + pair.Key + " " + pair.Value);
            return 1;
        }

        var game = match.GetProperty("game").GetString();
        var network = match.GetProperty("network").GetInt32();
        var constant = assemblies["assembly_valheim.dll"].ReadConstant(
            tested.GetProperty("network_constant").GetProperty("type").GetString()!,
            tested.GetProperty("network_constant").GetProperty("field").GetString()!);
        if (constant == null || Convert.ToInt32(constant) != network)
        {
            Console.WriteLine("NETWORK VERSION MISMATCH: dll=" + (constant ?? "missing") + " tested=" + network);
            failures++;
        }
        Console.WriteLine("build: Valheim " + game + ", network " + constant);
        return failures;
    }

    static string Describe(JsonElement entry)
    {
        var text = entry.GetProperty("type").GetString() + "." + entry.GetProperty("member").GetString();
        if (entry.TryGetProperty("params", out var parameters))
            text += "(" + string.Join(", ", parameters.EnumerateArray().Select(p => p.GetString())) + ")";
        return text;
    }

    static string? CheckMember(JsonElement entry, Dictionary<string, Assembly> assemblies)
    {
        var typeName = entry.GetProperty("type").GetString()!;
        var memberName = entry.GetProperty("member").GetString()!;
        var kind = entry.GetProperty("kind").GetString()!;
        var assemblyName = entry.TryGetProperty("assembly", out var a) ? a.GetString()! : "assembly_valheim.dll";
        var assembly = assemblies[assemblyName];
        var type = assembly.FindType(typeName);
        if (type == null)
            return "type not found in " + assemblyName;

        switch (kind)
        {
            case "type":
                return null;
            case "field":
                return assembly.HasField(type.Value, memberName) ? null : "field not found";
            case "property":
                return assembly.HasProperty(type.Value, memberName) ? null : "property not found";
            case "method":
                var overloads = assembly.MethodSignatures(type.Value, memberName);
                if (overloads.Count == 0)
                    return "method not found";
                if (!entry.TryGetProperty("params", out var wanted))
                    return null;
                var expected = wanted.EnumerateArray().Select(p => p.GetString()!).ToList();
                if (overloads.Any(o => o.SequenceEqual(expected)))
                    return null;
                return "no overload with these params; found: " +
                       string.Join(" | ", overloads.Select(o => "(" + string.Join(", ", o) + ")"));
            default:
                return "unknown kind " + kind;
        }
    }
}

sealed class Assembly
{
    readonly PEReader pe;
    readonly MetadataReader md;
    public string Sha256 { get; }

    Assembly(string path)
    {
        var bytes = File.ReadAllBytes(path);
        Sha256 = Convert.ToHexString(SHA256.HashData(bytes)).ToLowerInvariant();
        pe = new PEReader(ImmutableArray.Create(bytes));
        md = pe.GetMetadataReader();
    }

    public static Assembly Open(string path) => new Assembly(path);

    // "Outer/Inner" 표기로 중첩 타입을 찾는다. 네임스페이스가 있으면 "Ns.Type".
    public TypeDefinitionHandle? FindType(string name)
    {
        var parts = name.Split('/');
        TypeDefinitionHandle? current = null;
        foreach (var handle in md.TypeDefinitions)
        {
            var def = md.GetTypeDefinition(handle);
            if (def.GetDeclaringType().IsNil && FullName(def) == parts[0])
            {
                current = handle;
                break;
            }
        }
        for (int i = 1; i < parts.Length && current != null; i++)
        {
            TypeDefinitionHandle? next = null;
            foreach (var nested in md.GetTypeDefinition(current.Value).GetNestedTypes())
                if (md.GetString(md.GetTypeDefinition(nested).Name) == parts[i])
                    next = nested;
            current = next;
        }
        return current;
    }

    string FullName(TypeDefinition def)
    {
        var ns = md.GetString(def.Namespace);
        var name = md.GetString(def.Name);
        return ns.Length == 0 ? name : ns + "." + name;
    }

    public bool HasField(TypeDefinitionHandle type, string name) =>
        md.GetTypeDefinition(type).GetFields().Any(f => md.GetString(md.GetFieldDefinition(f).Name) == name);

    public bool HasProperty(TypeDefinitionHandle type, string name) =>
        md.GetTypeDefinition(type).GetProperties().Any(p => md.GetString(md.GetPropertyDefinition(p).Name) == name);

    public List<List<string>> MethodSignatures(TypeDefinitionHandle type, string name)
    {
        var result = new List<List<string>>();
        var provider = new TypeNames(md);
        foreach (var handle in md.GetTypeDefinition(type).GetMethods())
        {
            var method = md.GetMethodDefinition(handle);
            if (md.GetString(method.Name) != name)
                continue;
            var signature = method.DecodeSignature(provider, null);
            result.Add(signature.ParameterTypes.ToList());
        }
        return result;
    }

    public IEnumerable<string> Describe(TypeDefinitionHandle type)
    {
        var provider = new TypeNames(md);
        var def = md.GetTypeDefinition(type);
        foreach (var handle in def.GetFields())
        {
            var field = md.GetFieldDefinition(handle);
            var access = (field.Attributes & FieldAttributes.FieldAccessMask) == FieldAttributes.Public ? "public" : "private";
            var isStatic = (field.Attributes & FieldAttributes.Static) != 0 ? " static" : "";
            var isConst = (field.Attributes & FieldAttributes.Literal) != 0 ? " const" : "";
            yield return "field   " + access + isStatic + isConst + " " + field.DecodeSignature(provider, null) + " " + md.GetString(field.Name);
        }
        foreach (var handle in def.GetProperties())
        {
            var property = md.GetPropertyDefinition(handle);
            var signature = property.DecodeSignature(provider, null);
            yield return "prop    " + signature.ReturnType + " " + md.GetString(property.Name);
        }
        foreach (var handle in def.GetMethods())
        {
            var method = md.GetMethodDefinition(handle);
            var signature = method.DecodeSignature(provider, null);
            var access = (method.Attributes & MethodAttributes.MemberAccessMask) == MethodAttributes.Public ? "public" : "private";
            var isStatic = (method.Attributes & MethodAttributes.Static) != 0 ? " static" : "";
            var names = method.GetParameters().Select(p => md.GetParameter(p)).Where(p => p.SequenceNumber > 0)
                .OrderBy(p => p.SequenceNumber).Select(p => md.GetString(p.Name)).ToList();
            var parameters = signature.ParameterTypes.Select((t, i) => t + " " + (i < names.Count ? names[i] : "?"));
            yield return "method  " + access + isStatic + " " + signature.ReturnType + " " + md.GetString(method.Name) + "(" + string.Join(", ", parameters) + ")";
        }
        foreach (var nested in def.GetNestedTypes())
            yield return "nested  " + md.GetString(md.GetTypeDefinition(nested).Name);
    }

    public object? ReadConstant(string typeName, string fieldName)
    {
        var type = FindType(typeName);
        if (type == null)
            return null;
        foreach (var handle in md.GetTypeDefinition(type.Value).GetFields())
        {
            var field = md.GetFieldDefinition(handle);
            if (md.GetString(field.Name) != fieldName)
                continue;
            var constantHandle = field.GetDefaultValue();
            if (constantHandle.IsNil)
                return null;
            var constant = md.GetConstant(constantHandle);
            var blob = md.GetBlobReader(constant.Value);
            return constant.TypeCode switch
            {
                ConstantTypeCode.Int32 => blob.ReadInt32(),
                ConstantTypeCode.UInt32 => blob.ReadUInt32(),
                ConstantTypeCode.Int64 => blob.ReadInt64(),
                ConstantTypeCode.String => blob.ReadUTF16(blob.Length),
                _ => throw new NotSupportedException("constant type " + constant.TypeCode),
            };
        }
        return null;
    }
}

// 시그니처를 "System.Boolean", "UnityEngine.Vector3", "ItemDrop/ItemData&" 같은 이름으로 풀어 준다.
sealed class TypeNames : ISignatureTypeProvider<string, object?>
{
    readonly MetadataReader md;

    public TypeNames(MetadataReader md)
    {
        this.md = md;
    }

    public string GetPrimitiveType(PrimitiveTypeCode typeCode) => typeCode switch
    {
        PrimitiveTypeCode.Boolean => "System.Boolean",
        PrimitiveTypeCode.Byte => "System.Byte",
        PrimitiveTypeCode.Char => "System.Char",
        PrimitiveTypeCode.Double => "System.Double",
        PrimitiveTypeCode.Int16 => "System.Int16",
        PrimitiveTypeCode.Int32 => "System.Int32",
        PrimitiveTypeCode.Int64 => "System.Int64",
        PrimitiveTypeCode.IntPtr => "System.IntPtr",
        PrimitiveTypeCode.Object => "System.Object",
        PrimitiveTypeCode.SByte => "System.SByte",
        PrimitiveTypeCode.Single => "System.Single",
        PrimitiveTypeCode.String => "System.String",
        PrimitiveTypeCode.UInt16 => "System.UInt16",
        PrimitiveTypeCode.UInt32 => "System.UInt32",
        PrimitiveTypeCode.UInt64 => "System.UInt64",
        PrimitiveTypeCode.UIntPtr => "System.UIntPtr",
        PrimitiveTypeCode.Void => "System.Void",
        PrimitiveTypeCode.TypedReference => "System.TypedReference",
        _ => typeCode.ToString(),
    };

    public string GetTypeFromDefinition(MetadataReader reader, TypeDefinitionHandle handle, byte rawTypeKind)
    {
        var def = reader.GetTypeDefinition(handle);
        var name = reader.GetString(def.Name);
        var ns = reader.GetString(def.Namespace);
        var declaring = def.GetDeclaringType();
        if (!declaring.IsNil)
            return GetTypeFromDefinition(reader, declaring, rawTypeKind) + "/" + name;
        return ns.Length == 0 ? name : ns + "." + name;
    }

    public string GetTypeFromReference(MetadataReader reader, TypeReferenceHandle handle, byte rawTypeKind)
    {
        var reference = reader.GetTypeReference(handle);
        var name = reader.GetString(reference.Name);
        var ns = reader.GetString(reference.Namespace);
        if (reference.ResolutionScope.Kind == HandleKind.TypeReference)
            return GetTypeFromReference(reader, (TypeReferenceHandle)reference.ResolutionScope, rawTypeKind) + "/" + name;
        return ns.Length == 0 ? name : ns + "." + name;
    }

    public string GetTypeFromSpecification(MetadataReader reader, object? context, TypeSpecificationHandle handle, byte rawTypeKind) =>
        reader.GetTypeSpecification(handle).DecodeSignature(this, context);

    public string GetSZArrayType(string elementType) => elementType + "[]";
    public string GetArrayType(string elementType, ArrayShape shape) => elementType + "[" + new string(',', shape.Rank - 1) + "]";
    public string GetByReferenceType(string elementType) => elementType + "&";
    public string GetPointerType(string elementType) => elementType + "*";
    public string GetPinnedType(string elementType) => elementType;
    public string GetGenericInstantiation(string genericType, ImmutableArray<string> typeArguments) =>
        genericType + "<" + string.Join(",", typeArguments) + ">";
    public string GetGenericMethodParameter(object? context, int index) => "!!" + index;
    public string GetGenericTypeParameter(object? context, int index) => "!" + index;
    public string GetFunctionPointerType(MethodSignature<string> signature) => "fnptr";
    public string GetModifiedType(string modifier, string unmodifiedType, bool isRequired) => unmodifiedType;
}
