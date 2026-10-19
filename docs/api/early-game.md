# Valheim 초반(스폰 → Eikthyr) 메커니즘·API 노트

- **대상 빌드: Valheim 1.0.20**
  - `Version.CurrentVersion = (1, 0, 20)`, `Version.c_networkVersion = 41u`
  - Unity 6000.0.75f1(26349cd2a5c8, `Info.plist`와 `globalgamemanagers` 둘 다 같다)
  - Steam buildid 25909357(`appmanifest_892970.acf`). 2026-10-16 Steam 업데이트분이다.
- 확인일: 2026-10-17
- 방법
  - 설치 폴더의 DLL을 세션 scratchpad로 복사해 ilspycmd 9.1(.NET 9 roll-forward)로 디컴파일했다.
  - 1.0.16 DLL(런타임 클론)도 같은 방법으로 디컴파일해 diff했다. 시그니처는 `tools/Thorkell.ApiCheck --dump`로 비교했다.
  - 프리팹 값은 SoftRef 번들(`StreamingAssets/SoftRef/Bundles`, type tree 포함)을 UnityPy 1.25.4로 읽었다. 같은 스크립트로 1.0.16 클론의 번들도 읽어 비교했다.
  - 디컴파일 소스와 덤프는 레포에 넣지 않았다.
- **표기**
  - **[D]** = `[decompiled 1.0.20]`: 코드의 로직과 필드 기본값이다.
  - **[A]** = `[asset 1.0.20]`: 프리팹·ScriptableObject에 직렬화된 실제 값이다.
  - **프리팹 값이 있으면 코드 기본값보다 우선한다.** 위키 값은 쓰지 않았다(에셋에서 모두 읽혔다).
- `docs/api/1.0.16.md`에 있는 내용은 반복하지 않고 `→1.0.16 §X`로 가리킨다.
- 정보 동등성(AGENTS 규칙 5): 아래 prefab 이름(`Deer`, `Eikthyr`…)과 `$enemy_…`·`$item_…` 토큰은 몸과 문서에서만 쓴다. 두뇌 프롬프트에 넣지 않는다.

---

## 0. 1.0.16 → 1.0.20 변경점

### 0.1 버전 상수 [D]
| 항목 | 1.0.16 | 1.0.20 |
|---|---|---|
| `Version.CurrentVersion` | 1.0.16 | **1.0.20** |
| `Version.c_networkVersion` (const) | 40 | **41** |
| `c_WorldVersion` (`Version.World`) | DeepNorth = 41 | **CheatCleanSlate = 42** |
| `c_PlayerVersion` (프로필 `.fch`) | DeepNorth = 46 | **CheatCleanSlate = 47** |
| `c_PlayerDataVersion` | ChunkedNorth = 33 | **PostLaunch = 34** |
| `c_ItemDataVersion` | ChunksNCheats = 109 | **NewCheats = 110** |
| chunk·ZDO·`.db2` 저장 헤더 | 41 | 42 |
| Unity | 6000.0.75f1 | 6000.0.75f1 (같음) |

### 0.2 해시와 `tested-versions.json`
| 파일 | 1.0.20 sha256 (설치본) | 1.0.16 (클론) |
|---|---|---|
| `assembly_valheim.dll` | `584ffa945642e5f6af7b027d77f14009ca2553ea6d22ab4b810a51513628afad` | `141dce5a…b986` |
| `assembly_utils.dll` | `f1a71a7b1d315d476f21d3c45f96e79a9d94cc9911db523704dd496aea76f3e3` | `4ba2cc87…30e3` |
| `Splatform.Steam.dll` | `04c32485b93f15cef6292f152d4c824cf4cf52636a0f58820a2340969bc24abd` | 같음 |

- 바뀐 DLL은 `assembly_valheim`, `assembly_utils`, `Assembly-CSharp` 셋뿐이다. `assembly_utils`와 `Assembly-CSharp`는 디컴파일 결과가 같고 재빌드만 됐다.
- `tested-versions.json`
  - 커밋(HEAD 82916a5)에는 1.0.16 항목만 있다. 그 상태로는 1.0.20에서 버전 게이트가 arm을 거부한다(의도된 동작).
  - 2026-10-17 작업 트리에는 다른 작업이 `{game "1.0.20", network 41, unity "6000.0.75f1", sha256 위 2개}` 항목을 이미 넣어 두었다. 값은 이 문서와 같다. 이 작업은 그 파일을 고치지 않았다.
- `RequiredApi.json`: scratchpad로 복사한 DLL에 ApiCheck를 돌렸다.
  - 커밋 버전(87개): 1.0.20에서 **87개 멤버가 모두 있다.** 실패는 빌드 해시 불일치 1건뿐이었다.
  - 작업 트리 버전(99개, 제작·건축용 private 멤버 추가): 1.0.16과 1.0.20 모두 `OK: 99 members present, build matches`.

### 0.3 시그니처 diff
비교 범위
- RequiredApi 타입 33개
- 이 문서가 다루는 타입 45개: CraftingStation, InventoryGui, Player, Recipe, Piece, PieceTable, Humanoid, ItemDrop, Attack, Character, EnemyHud, Raven, RuneStone, Vegvisir, ItemStand, DamageText, BaseAI, MonsterAI, AnimalAI, CharacterDrop, OfferingBowl, Location, Pickable, TreeBase, TreeLog, Destructible, MineRock(5), CookingStation, Fireplace, SE_Rested, SE_Stats, StatusEffect, Bed, TombStone, Inventory, Skills, MessageHud, Game, SpawnSystem, Projectile, ObjectDB, Container, WearNTear, Hud, Tutorial 등

**이름이 바뀌거나 지워진 멤버는 없다.** 바뀐 것:

| 타입 | 변경 |
|---|---|
| `CharacterDrop` | `public static Dictionary<string, Tuple<float,int>> s_pseudoCounter` → **`Dictionary<int,int>`** |
| `CharacterDrop.Drop` | 새 필드 `public bool m_levelMultiplierNotAmount` |
| `ItemDrop` | 새 메서드 `private void OnValidate()`, `public void EnsureValid()` |
| `Player` | 새 필드 `private Dictionary<int,int> m_itemUpgradeSeeds`, 새 메서드 `public float GetItemUpgradeChance(int hash)` |
| (새 타입) | `internal static class CheatUtils`: `ZDO.IsCheated()`, `IsCheated(bool)`[Obsolete], `SetCheated()`, `SetCheated(bool)`, `RemoveCheated()`, `ItemData.HasCheatedProperties()` |

### 0.4 Thorkell에 영향이 있는 동작 변경
1. **cheated 표시 방식이 바뀌었다(`CheatCleanSlate`).** →1.0.16 §E 아래 "F 연관"은 이제 틀린 설명이다.
   - ZDO의 `s_cheated`는 bool이 아니라 **int 2**다(`c_CheatRevision = 2`). `IsCheated() == (GetInt(s_cheated) == 2)`이다.
   - 1.0.16이 남긴 bool `true`는 더 이상 cheated로 보지 않는다.
   - `ItemData.m_cheated`는 아이템 저장 버전이 110 이상일 때만 읽는다. 1.0.20 이전에 저장된 아이템은 모두 cheated가 풀린다.
   - "피해 10000 초과면 cheated" 판정은 `Inventory.AddItem`에서 `ItemDrop.EnsureValid()`로 옮겨졌다.
   - `Inventory.AddItem(…, cheated: true)` 자체는 그대로 동작한다.
   - 따라서 감사 도구가 ZDO를 직접 읽는다면 `GetInt(s_cheated) == 2`로 비교해야 한다.
2. **저장과 네트워크가 호환되지 않는다.**
   - 1.0.20은 월드 42, 프로필 47, PlayerData 34, 아이템 110 버전으로 저장한다.
   - 1.0.16의 `Version.IsWorldVersionCompatible`은 41 이하만 받는다. 그래서 **1.0.20이 한 번이라도 저장한 월드·캐릭터는 1.0.16 클론에서 열리지 않는다**(리허설, 백업 복원 포함).
   - 네트워크 버전이 40과 41로 다르다. `ZNet.RPC_PeerInfo`가 버전 불일치로 거절한다(→1.0.16 §A2의 1단계, Error 3).
   - 결과: **1.0.16 봇 클론은 사람의 1.0.20 호스트에 들어갈 수 없다.** 1.0.16 호스트 클론에는 1.0.20 친구가 들어올 수 없다.
   - 런타임 클론(`~/Library/Application Support/Thorkell/runtimes/*`)을 1.0.20으로 다시 떠야 한다.
3. **pseudo-random 드롭** [D]
   - 확률이 `≤ 0.3`인 드롭(레벨 배수를 적용한 뒤 기준)은 카운터로 나온다. 전역 키 `NoPseudoDrops`가 있으면 끈다.
   - 키는 `prefab이름.GetStableHashCode() + (int)(chance*1000)`이다(1.0.16에서는 prefab 이름 문자열).
   - 카운터 초기값은 `Random.Range(0, (int)(2/p))`이다. 드롭이 나면 `Random.Range(0, (int)(2/p)+2)`로 다시 정한다(1.0.16은 `(int)(2/p+1)`).
   - 카운터는 `CharacterDrop.OnDeath`를 실행한 프로세스, 즉 **그 생물의 소유자**에 있다. 그 프로세스의 캐릭터 저장(PlayerData 34)에 함께 저장된다.
4. **트로피 드롭에 레벨 배수가 붙었다** [A diff]
   - Deer, Boar, Neck, Greydwarf, Eikthyr의 트로피가 `m_levelMultiplier` 0→1, `m_levelMultiplierNotAmount`=1로 바뀌었다.
   - 확률이 `×2^(level−1)`이 된다(★1 ×2, ★2 ×4). 개수는 그대로 1개다.
   - 예: ★1 사슴의 트로피 확률은 0.5×2 = 1.0이다.
5. 업그레이더 강화 확률이 플레이어별 시드(이름 해시+아이템 해시)로 결정적이 됐다. 초반과는 관계없다.
6. **에셋은 1.0.16과 같다** [A diff]
   - 레시피 481개 전체, 아래 아이템·조각·생물·Player·채집물·EnemyHud·ZoneCtrl 프리팹은 위 4번 말고는 차이가 없다.
   - StartTemple·Eikthyrnir 번들은 바이트까지 같다.

### 0.5 1.0.16.md 정정 (코드 기본값 ≠ 프리팹 값, 1.0.16에서도 같은 프리팹 값)
| 항목 | 1.0.16.md (코드 기본값) | 실제 [A] |
|---|---|---|
| `Player.m_maxInteractDistance` (§D, §G "줍기 거리") | 5 | **3.5** (+ 대상 `GetHoverOffset()`) |
| `Player.m_maxPlaceDistance` | 5 | **8** |
| `EnemyHud.m_maxShowDistance` (§E) | 10 | **30** (보스 100, hover 유지 60초) |
| `EnvMan.m_dayLengthSec` | 1200 | **1800** (밤 = 일 비율 <0.25 또는 >0.75 = 900초) |
| `Player.m_hardDeathCooldown` | 10 | **600** |

---

## 1. 제작

### 1.1 `CraftingStation` [D] + 작업대 프리팹 [A]
| 필드 | 코드 기본값 [D] | `piece_workbench` [A] |
|---|---|---|
| `m_name` | "" | `$piece_workbench` |
| `m_discoverRange` | 4 | 4 |
| `m_rangeBuild` | 10 | **20** |
| `m_extraRangePerLevel` | 0 | 4 |
| `m_craftRequireRoof` | true | true |
| `m_craftRequireFire` | true | **false** |
| `m_useDistance` | 2 | 2 |
| `m_showBasicRecipies` | false | **true** |
| `m_canRepair` / `m_upgrader` / `m_hasCraftTab` | true / false / true | true / false / true |
| `m_craftingSkill` | Crafting | Crafting |
| PlayerBase EffectArea | — | 반경 20 |

| 시그니처 | 동작과 메시지 |
|---|---|
| `public bool Interact(Humanoid user, bool repeat, bool alt)` | `repeat`이면 false다. 로컬 플레이어이고 `InUseDistance`여야 한다. `CheckUsable(player, true)`를 통과하면 `player.SetCraftingStation(this)` → `InventoryGui.instance.Show(null, 3)`. **항상 false를 돌려준다**(상호작용 애니메이션 없음). |
| `public bool InUseDistance(Humanoid human)` | **`transform.position` 사이 거리 < `m_useDistance`(2m).** 콜라이더 표면이 아니라 루트 기준이다. 멀면 아무 메시지 없이 실패한다. hover 글은 `$piece_toofar`. |
| `public bool CheckUsable(Player player, bool showMessage)` | 지붕: `Cover.GetCoverForPoint(m_roofCheckPoint.position)`. `!underRoof`면 `$msg_stationneedroof`, cover < 0.7이면 `$msg_stationtooexposed`. 불: `!m_haveFire`면 `$msg_needfire`(`CheckFire`가 1초마다 `EffectArea.IsPointPlus025InsideBurningArea(pos)`로 갱신). |
| `public float GetStationBuildRange()` | `m_rangeBuild + 확장 수 × m_extraRangePerLevel`. 확장 목록은 2초마다 갱신한다. |
| `public int GetLevel(bool checkExtensions = true)` | `1 + 확장 수`. 확장(`StationExtension.m_maxStationDistance` 5m 안, 같은 종류는 1개만): ext1 작업대(Wood 10, Flint 10), ext2(Wood 10, Flint 15, LeatherScraps 20, DeerHide 5) [A]. 둘 다 `m_spaceRequirement` 2, 기울어진 땅 불가. |
| `public static CraftingStation HaveBuildStationInRange(string name, Vector3 point)` | 점의 y를 스테이션 높이로 맞춘 뒤 거리 < 건축 범위. |
| `public static void UpdateKnownStationsInRange(Player)` | 거리 < `m_discoverRange`(4m)이면 `AddKnownStation`. `Player.UpdateStations`가 1초마다 부른다. |
| `Player.UpdateStations(dt)` (private) | 현재 스테이션에서 `!InUseDistance`이면 `InventoryGui.Hide()`. `!InventoryGui.IsVisible()`이면 스테이션을 해제한다. 사용 중에는 몸을 스테이션 쪽으로 돌린다. |
| `Player.SetCraftingStation(CraftingStation)` (public) | `AddKnownStation`, `HideHandItems()`. |

### 1.2 `Cover` (`assembly_utils`, 1.0.16과 같음) [D]
- `public static void GetCoverForPoint(Vector3 startPos, out float coverPercentage, out bool underRoof, float minDistance = 0.5f)`
  - 레이 17개(위 1, 수평 8, 대각선 위 8)를 길이 29.5로 쏜다.
  - 마스크: Default, static_solid, Default_small, piece, terrain, vehicle.
  - cover = 맞은 수 / 17.
- `public static bool IsUnderRoof(Vector3)`: 반지름 0.1 SphereCast를 위로 100m 쏜다. tag가 `leaky`가 아닌 것을 맞히면 true.
- 기준값

| 사용처 | 조건 |
|---|---|
| 작업대 | underRoof + cover ≥ 0.7 |
| 침대 | spawn point 기준 underRoof + cover ≥ 0.8 |
| `Player.InShelter()` | 1초마다 `GetCenterPoint()` 기준 underRoof + cover ≥ 0.8 |
| 모닥불 젖음 | 바람 ≥ 0.8이고 cover < 0.7, 또는 비가 오고 지붕이 없음 |

### 1.3 `InventoryGui` 제작 흐름 [D]
- 필드
  - 시간: `m_craftDuration 2`, `m_multiCraftAmount 5`, `m_multiCraftDuration 6`, `m_craftDurationSkillMaxDecrease 0.6`
  - 보너스: `m_craftBonusChance 0.25`, `m_craftBonusAmount 1`
  - 상태: `private float m_craftTimer = -1`, `private RecipeDataPair m_selectedRecipe`, `private List<RecipeDataPair> m_availableRecipes`
  - `RecipeDataPair`는 private struct `{Recipe, ItemData, InterfaceElement, CanCraft}`이다.
  - UI: `public Button m_craftButton`

| 단계 | 시그니처 | 내용 |
|---|---|---|
| 열기 | `public void Show(Container container, int activeGroup = 1)` | `SetupCrafting` → `UpdateCraftingPanel` → `Player.GetAvailableRecipes` → `UpdateRecipeList`. 정렬은 제작 가능 여부(내림차순) → `m_listSortWeight` → 이름. 기본 선택은 0번. |
| 선택 | `private void OnSelectedRecipe(GameObject button)` → `private void SetRecipe(int index, bool center)` | 목록 항목의 `Button.onClick`에 연결돼 있다. |
| 매 프레임 | `private void UpdateRecipe(Player, float dt)` | 보일 때만 돈다. `m_craftButton.interactable = HaveRequirements(recipe, false, q, n) && (스테이션 불필요 \|\| 현재 스테이션.CheckUsable(false))`. 툴팁은 `$msg_missingrequirement` / `$msg_missingstation` / `$inventory_full`. |
| 누름 | `private void OnCraftPressed()` (`m_craftButton.onClick`) | `AltPlace`를 누르고 있으면 5개 제작. `CanAddItem` 실패 시 `$inventory_full`. `m_craftTimer = 0`. **요건은 다시 확인하지 않는다.** |
| 대기 | `UpdateRecipe` 안 | 소요 시간 = (5개 제작이면 6, 아니면 2) × (1 − Crafting 스킬계수 × 0.6). 스테이션이 없으면 감소 없이 2초다. |
| 완료 | `private void DoCrafting(Player)` | 요건을 다시 확인한다. 스택형 결과물이면 1회당 스킬×0.25 확률로 +1. → `Inventory.AddItem(prefab이름, n, q, variant, crafterID, crafterName, cheated)` → `Player.ConsumeResources(recipe.m_resources, q, -1, 배수)` → `UpdateCraftingPanel` → `RaiseSkill(스테이션 스킬, 1 또는 5)`. |
| 취소 | `Hide()`, `OnCraftCancelPressed()` | `m_craftTimer = -1`. |

- 함정
  - `InventoryGui.Update`는 화면이 보일 때 **`Inventory`, `JoyButtonB/Y`, `Escape`, `Use`를 누르면 닫힌다**(`m_shownFrames > 1`).
  - 제작 중 Use 입력은 곧 취소다.
  - `InventoryGui.IsVisible()`이면 `Player.TakeInput()`이 false라서 이동할 수 없다.

### 1.4 요건 확인과 자원 소비 [D]
- `public bool HaveRequirements(Recipe recipe, bool discover, int qualityLevel, int amount = 1)`
- `public bool RequiredCraftingStation(Recipe recipe, int qualityLevel, bool checkLevel)`
  - 필요 스테이션은 `recipe.GetRequiredStation(q)`이다(`m_craftingStation`, 없고 q>1이면 `m_repairStation`).
  - 현재 스테이션의 `m_name`이 같아야 한다. `GetLevel() ≥ max(1, m_minStationLevel) + (q−1)`이어야 한다.
  - **스테이션이 없는 레시피도, 현재 스테이션의 `m_showBasicRecipies`가 false면 거부한다.** 작업대는 true라 괜찮다.
- 개수 판정(private `HaveRequirementItems`)
  - 자원마다 **품질별 `CountItems(name, q)` 가운데 최댓값**을 본다. 합계가 아니다.
  - 그 값이 `Requirement.GetAmount(q) × amount` 이상이어야 한다.
- `public bool HaveRequirements(Piece piece, RequirementMode mode)`: mode는 `IsKnown`, `CanAlmostBuild`, `CanBuild`다.
  - 스테이션이 필요한 조각
    - IsKnown·CanAlmostBuild: `m_knownStations`에 그 이름이 있어야 한다.
    - CanBuild: `HaveBuildStationInRange(name, 플레이어 위치)`여야 한다.
  - 자원: `m_amount > 0`인 것만 본다.
    - IsKnown: 그 재료를 알아야 한다.
    - CanAlmostBuild: 1개라도 있어야 한다.
    - CanBuild: `CountItems ≥ m_amount`.
- `public void ConsumeResources(Piece.Requirement[] requirements, int qualityLevel, int itemQuality = -1, int multiplier = 1)`: `Inventory.RemoveItem(name, GetAmount(q)×multiplier, itemQuality)`. 업그레이더 자원은 업그레이더 스테이션에서만 센다.
- `Piece.Requirement.GetAmount(int q)`
  - q ≤ 1 → `m_amount`
  - 2 ≤ q ≤ 3 → `(q−1)×m_amountPerLevel`
  - q ≥ 4 → `floor((4 + (q−4)/2)×m_amountPerLevel)`
  - 조각을 지을 때는 q=0을 쓴다.

### 1.5 레시피·조각 해금 [D]
- 저장 필드(→1.0.16 §E): `m_knownRecipes`(레시피는 결과 아이템 `m_shared.m_name`, 조각은 `Piece.m_name`), `m_knownMaterial`, `m_knownStations`(이름 → 레벨).
- `OnInventoryChanged` → 모든 아이템에 `AddKnownItem` → 새 재료면 `$msg_newmaterial` / `$msg_newtrophy` / `$msg_newitem` → `UpdateKnownRecipesList()`.
- `private void UpdateKnownRecipesList()`
  - **레시피**: 활성화돼 있고 아직 모르는 레시피 가운데 `HaveRequirements(recipe, discover:true, 0)`인 것을 배운다.
    - 레시피에 스테이션이 있으면 그 스테이션을 `m_minStationLevel` 이상으로 알아야 한다.
    - `m_amount > 0`인 자원을 모두 알아야 한다.
    - → `AddKnownRecipe` → `$msg_newrecipe`
  - **조각**: 인벤토리에 있는 도구(망치 등)의 PieceTable에서, 스테이션(있다면)과 자원을 모두 알면 배운다. → `AddKnownPiece` → `$msg_newpiece`(음식 카테고리는 `$msg_newdish`) → `UpdateAvailablePiecesList()`.
- `AddKnownStation`: 처음이면 `$msg_newstation`, 레벨이 오르면 `$msg_newstation_level`. 레시피 목록을 다시 계산한다.
  - 계기: 4m 안 접근, `SetCraftingStation`, 스테이션을 직접 설치(`PlacePiece`).
- 따라서 L1 수량이 0인 재료는 해금을 막지 않는다. 예: Club의 BoneFragments, AxeFlint의 LeatherScraps.
- `public void GetAvailableRecipes(ref List<Recipe> available)`: 알고 있고(또는 NoPlacementCost / `AllRecipesUnlocked`) `RequiredCraftingStation(recipe, 1, checkLevel:false)`인 것.

### 1.6 `Recipe` 필드 [D]
| 필드 | 기본값 | 필드 | 기본값 |
|---|---|---|---|
| `m_item` (ItemDrop) | — | `m_craftingStation` | null |
| `m_amount` | 1 | `m_repairStation` | null |
| `m_enabled` | true | `m_minStationLevel` | 1 |
| `m_qualityResultAmountMultiplier` | 1 | `m_requireOnlyOneIngredient` | false |
| `m_listSortWeight` | 100 | `m_resources` (Piece.Requirement[]) | [] |
| `m_noCraftOnlyUpgrade` | false | | |

- 메서드: `GetRequiredStationLevel(int q)`, `GetRequiredStation(int q)`, `GetAmount(int q, out int need, out ItemData singleReqItem, int craftMultiplier = 1)`.
- `Piece.Requirement`: `m_resItem`, `m_amount = 1`, `m_extraAmountOnlyOneIngredient`, `m_amountPerLevel = 1`, `m_upgraderResource`, `m_recover = true`.

---

## 2. 건축 [D]

### 2.1 모드와 선택
- `public override bool InPlaceMode()` = `m_buildPieces != null`이다.
  - `Humanoid.SetupEquipment`가 오른손 아이템의 `m_shared.m_buildPieces`로 `SetPlaceMode`를 부른다.
  - 망치(`$item_hammer`, ItemType Tool, `m_equipDuration 0` [A])를 들면 `_HammerPieceTable`이 된다.
- `PieceTable` 필드: `m_pieces`, `m_categories`, `m_canRemovePieces`, `m_skill`.
  - `UpdateAvailable(HashSet<string> known, Player, bool hideUnavailable, bool noPlacementCost)`: 아는 조각만 사용할 수 있게 한다.
  - `GetPieceIndex(Piece, out Vector2Int, out PieceCategory)`, `SetSelected(Vector2Int)`, `SetCategory(int | PieceCategory)`, `GetSelectedPiece()`.
- Player의 선택 API

| 시그니처 | 동작 |
|---|---|
| `public bool SetSelectedPiece(Piece p)` | 사용 가능한(아는) 조각이면 카테고리와 인덱스를 고르고 고스트를 다시 만든다. 아니면 false. |
| `public void SetSelectedPiece(Vector2Int p)` | 인덱스로 고른다. |
| `GetSelectedPiece()`, `IsPieceAvailable(Piece)`, `GetBuildPieces()`, `SetBuildCategory(int \| PieceCategory)`, `public PlacementStatus GetPlacementStatus()`, `public bool CanRotatePiece()` | |

- 회전: `private int m_placeRotation`을 한 칸에 22.5°씩 돌린다(`m_placeRotationDegrees`). 휠 누적값이 `m_scrollAmountThreshold`를 넘으면 ±1이다. `Piece.m_canRotate`인 조각만 돌아간다.
- `BuildMenu`(우클릭)가 Hud 조각 선택창을 연다. 열려 있으면 `UpdatePlacement`가 바로 반환해서 설치되지 않는다.

### 2.2 고스트 배치 `private void UpdatePlacementGhost(bool flashGuardStone)`
- 레이 (`PieceRayTest`)
  - **`GameCamera.instance.transform`에서 정면으로 50m** 쏜다(물 조각은 물 마스크).
  - 맞은 점이 **눈(`m_eye`)에서 `m_maxPlaceDistance`(8 [A]) + `Piece.m_extraPlacementDistance` 안**이어야 한다.
  - 리지드바디가 붙은 콜라이더는 제외한다.
- 고스트 위치
  - 고스트 콜라이더에서 맞은 점과 가장 가까운 점이 그 점에 닿게 놓는다.
  - `AltPlace`를 누르지 않았으면 0.5m 안의 스냅 포인트에 붙인다. `TabLeft`/`TabRight`는 수동 스냅이다(`$msg_snapping`).
- 상태 판정 결과는 `PlacementStatus`다. `TryPlacePiece`가 아래 메시지를 띄운다.

| `PlacementStatus` | 메시지 | 초반 원인 |
|---|---|---|
| Valid | — | |
| Invalid, NoRayHits | `$msg_invalidplacement` | 범위 밖 또는 허공. `m_notOnWood`인데 나무 조각 위(**모닥불**). `m_notOnTiltingSurface`인데 normal.y < 0.8(**작업대**). `m_noInWater`인데 물. 대상 WearNTear의 `!m_supports`. `m_groundOnly`인데 지형이 아님. |
| BlockedbyPlayer | `$msg_blocked` | 고스트 콜라이더가 30m 안 Character(자기 자신·리더 포함)와 겹침 |
| NoBuildZone | `$msg_nobuildzone` | `Location.m_noBuild` 안(StartTemple 반경 25). Eikthyrnir는 noBuild=0. |
| PrivateZone | `$msg_privatezone` | 남의 와드 |
| MoreSpace | `$msg_needspace` | 확장 `m_spaceRequirement` 안에 다른 확장, 또는 블로킹 조각 |
| ExtensionMissingStation | `$msg_extensionmissingstation` | 5m 안에 작업대가 없음 |
| WrongBiome / NeedCultivated / NeedDirt / NotInDungeon / DeepSnow / NoSnow / NoTeleportArea | `$msg_wrongbiome` / `$msg_needcultivated` / `$msg_needdirt` / `$msg_notindungeon` / `$msg_snowtoodeep` / `$msg_nosnow` / `$msg_noteleportarea` | 초반에는 거의 없음 |

### 2.3 설치 경로 (`private void UpdatePlacement(bool takeInput, float dt)`)
1. `Attack` 또는 `JoyPlace` ButtonDown → `m_placePressedTime`.
2. 0.2초 안이고, 마지막 도구 사용 뒤 `m_placeDelay`(0.4초)가 지났으면 계속한다.
3. `HaveStamina(오른손.m_attack.m_attackStamina)`가 아니면 스태미나 바만 깜박인다.
4. 수리 조각이면 `Repair(tool, piece)`, 제거 조각이면 `RemovePiece()`를 한다.
5. 그 밖에는 `HaveRequirements(piece, CanBuild)`를 확인한다. 실패하면 `$msg_missingrequirement`.
6. → `public bool TryPlacePiece(Piece piece)`: 고스트 상태 판정 → 메시지 또는 `PlacePiece(piece, 고스트.pos, 고스트.rot, doAttack:true, cheated)`.
7. 성공하면
   - `ConsumeResources(piece.m_resources, 0)`(free-build 키가 없을 때)
   - `UseStamina(GetBuildStamina())`: 망치 공격 스태미나 5 [A] × (1+장비 보정) × (1 − 0.5×스킬)
   - `RaiseSkill(m_buildPieces.m_skill)`(제거 부채가 있으면 그것부터 깎는다)
   - 내구도 −`m_useDurabilityDrain`×(1 − `m_placementDurabilityMax`×스킬)
- `public void PlacePiece(Piece piece, Vector3 pos, Quaternion rot, bool doAttack = true, bool cheated = false)`
  - Instantiate → 크래프팅 스테이션이면 `AddKnownStation` → `Piece.SetCreator(playerID, platformUserID)` → `WearNTear.OnPlaced`.
  - 공격 애니메이션 → `IPlaced.OnPlaced` → `AddNoise(50)` → cheated면 `SetCheated`.
  - **요건, 스태미나, 자원 소비를 하지 않는다**(치트·도구용 경로).
- 제거: `Remove` ButtonUp 후 0.2초 안, `m_removeDelay` 0.25초가 지났을 때. 카메라에서 50m 레이를 쏘고 눈에서 `m_maxPlaceDistance` 안이어야 한다.

### 2.4 `Piece`의 필요 자원과 편안함 [D]
- 필드
  - `m_name`, `m_category`(Misc 0, Crafting 1, BuildingWorkbench 2, BuildingStonecutter 3, Furniture 4 …)
  - `m_comfort`, `m_comfortGroup`(None, Fire, Bed, Banner, Chair, Table …)
  - `m_craftingStation`, `m_resources`
  - 배치 제약 bool: `m_groundOnly`, `m_notOnWood`, `m_notOnTiltingSurface`, `m_noInWater`
  - `m_onlyInBiome`, `m_canRotate`, `m_canBeRemoved`, `m_extraPlacementDistance`
- 편안함: `SE_Rested.CalculateComfortLevel(bool inShelter, Vector3 pos)`
  - 기본 1이다. **은신처 안이면** +1을 하고, 10m 안 조각의 comfort를 더한다.
  - 같은 comfortGroup은 가장 높은 것 하나만, 같은 이름도 하나만 센다.
  - 초반에 편안함을 주는 조각은 fire_pit(Fire, 1)과 bed(Bed, 1)뿐이다 [A]. 그래서 최대 4다.

---

## 3. 장착과 아이템 [D] (수치는 [A])
- `public bool EquipItem(ItemDrop.ItemData item, bool triggerEquipEffects = true)`
  - 실패 조건: 이미 장착함, 인벤토리에 없음, InAttack 또는 InDodge, 땅에 닿지 않고 수영 중, **`m_useDurability`이고 `m_durability ≤ 0`**, DLC.
  - Tool(망치·괭이)을 들면 양손을 비운다.
  - Torch: 오른손이 OneHanded이고 왼손이 비었으면 왼손, 아니면 오른손.
  - OneHanded는 오른손이다.
- `public void UseItem(Inventory inventory, ItemDrop.ItemData item, bool fromInventoryGui)`
  1. `!fromInventoryGui`이고 hover 대상의 `Interactable.UseItem(this, item)`이 true면 상호작용 애니메이션을 하고 끝낸다. 제물 그릇, 요리대, 모닥불 연료, 아이템 거치대가 여기에 해당한다.
  2. 아니면 Consumable은 `ConsumeItem`, 그 밖에는 `ToggleEquipped`.
  3. 실패하면 `$msg_cantuseon`(hover가 있을 때) 또는 `$msg_useonwhat`.
- `public void UseHotbarItem(int index)` = `UseItem(null, GetItemAt(index−1, 0), false)`. 단축바는 첫 줄 1~8번이다.
- `Player.ToggleEquipped` (protected override)
  - InAttack이면 입력을 먹고 아무것도 하지 않는다.
  - `m_equipDuration ≤ 0`이면 즉시 장착한다. 아니면 `MinorActionData`(Equip/Unequip, `$hud_equipping`)를 큐에 넣는다.
  - 장착 시간 [A]: 도구·무기 0.2초(망치 0), 가슴·다리·망토 **2초**, 투구 1초.
  - **달리기(`CheckRun`), 공격 시작, 회피가 `ClearActionQueue`를 부른다.** 큐에 넣은 장착이 취소된다.
- 내구도
  - 근접 공격은 **1개 이상 맞혔을 때** `m_useDurabilityDrain`만큼 준다. 투사체는 발사할 때마다, 건축과 제거는 `GetPlaceDurability`만큼 준다.
  - 막기는 `drain × 막을 수 있는 피해 / 막기 힘`만큼 준다.
  - 장착 중 계속 닳는 것: `m_durabilityDrain`/초(횃불 0.0333 [A]). 0이 되면 `$msg_broke`, 장착 해제, `m_destroyBroken`이면 삭제.
  - `GetMaxDurability(q) = m_maxDurability + (q−1)×m_durabilityPerLevel`.
  - **코드상 장착된 무기·도구는 내구도 0이 돼도 자동으로 해제되지 않는다.** 다시 장착만 막는다. 실게임에서 확인하지 않았다.
- `ItemDrop.ItemData.SharedData` 주요 필드(코드 기본값)
  - 기본: `m_name`, `m_itemType`, `m_maxStackSize 1`, `m_maxQuality 1`, `m_weight 1`, `m_equipDuration 1`
  - 음식: `m_food`, `m_foodStamina`, `m_foodEitr`, `m_foodBurnTime`, `m_foodRegen`, `m_foodEatAnimTime 1`, `m_consumeStatusEffect`
  - 방어: `m_armor 10`, `m_armorPerLevel 1`, `m_blockPower 10`, `m_blockPowerPerLevel`, `m_timedBlockBonus 1.5`, `m_deflectionForce`
  - 공격: `m_skillType`, `m_toolTier`, `m_damages`, `m_damagesPerLevel`, `m_attackForce 30`, `m_backstabBonus 4`, `m_attack`, `m_secondaryAttack`, `m_ammoType`, `m_movementModifier`
  - 내구도: `m_useDurability`, `m_maxDurability 100`, `m_durabilityPerLevel 50`, `m_useDurabilityDrain 1`, `m_durabilityDrain`, `m_canBeReparied true`, `m_destroyBroken true`
  - 건축: `m_buildPieces`

---

## 4. 음식 [D] (수치는 [A])
- `Player.m_foods`(private `List<Food>`)
  - `Food`의 필드: `m_name`(prefab), `m_item`, `m_time`, `m_health`, `m_stamina`, `m_eitr`.
  - **슬롯은 3개다**(코드 상수).
  - 공개 조회: `public List<Food> GetFoods()`.
- 시그니처
  - `public bool CanEat(ItemDrop.ItemData item, bool showMessages)`
  - `public bool EatFood(ItemDrop.ItemData item)`
  - `public override bool CanConsumeItem(ItemDrop.ItemData item, bool checkWorldLevel = false)`
  - `public override bool ConsumeItem(Inventory inventory, ItemDrop.ItemData item, bool checkWorldLevel = false)`
- 규칙
  - 같은 음식은 남은 시간이 `m_foodBurnTime/2`보다 작을 때만 다시 먹을 수 있다. 아니면 `$msg_nomore`.
  - 3칸이 차 있고 반 아래인 음식이 없으면 `$msg_isfull`.
  - 3칸이 찼을 때는 반 아래인 음식 가운데 가장 많이 줄어든 것을 바꾼다.
  - 먹으면 Center 메시지 `" +X $item_food_health  +Y $item_food_stamina"`가 뜬다.
  - 음식이 처음 인벤토리에 들어오면 튜토리얼 `food`가 뜬다.
- 감소: 1초마다(× `Game.m_foodRate`) 계수 `f = clamp01(time/burn)^0.3`를 다시 계산한다. hp = 음식 hp × f, 스태미나도 같다. 끝나면 `$msg_food_done`.
- **최대 HP = `m_baseHP` 25 + Σ 음식 hp, 최대 스태미나 = `m_baseStamina` 50 + Σ 음식 스태미나** [A].
  - `Character.m_health`(Player 프리팹 100)는 플레이어 최대 HP에 쓰이지 않는다.
- **HP 회복**: 10초마다 `Σ m_foodRegen × SE 배수`만큼 회복한다(Rested ×1.5, Resting ×3, Wet ×0.75, Cold ×0.5 [A]).
  - **음식이 없으면 HP가 자연 회복되지 않는다.** 굶주림 피해는 없다.
- **스태미나 회복**: 초당 `(m_staminaRegen 6 + (1 − s/max) × 6) × SE 배수 × Game.m_staminaRegenRate`.
  - 막는 중이면 ×0.8이다. 공격, 회피, 땅에 닿지 않은 수영, 과적 중에는 0이다.
  - `UseStamina`를 할 때마다 `m_staminaRegenDelay` 1초 동안 멈춘다 [A].

| 음식 [A] | HP | 스태미나 | 지속(초) | 회복/10초 | 얻는 곳 |
|---|---|---|---|---|---|
| Raspberry `$item_raspberries` | 7 | 20 | 600 | 1 | RaspberryBush (300분마다 다시 자람) |
| Blueberries | 8 | 25 | 600 | 1 | 흑림 |
| Mushroom | 15 | 15 | 900 | 1 | Pickable_Mushroom (240분) |
| MushroomYellow | 10 | 30 | 600 | 1 | |
| Honey | 8 | 35 | 900 | 1 | 벌통 |
| CookedMeat `$item_boar_meat_cooked` | 30 | 10 | 1200 | 2 | RawMeat를 요리대에 |
| NeckTailGrilled | 25 | 8 | 1200 | 2 | NeckTail을 요리대에 |
| CookedDeerMeat | 35 | 12 | 1200 | 2 | DeerMeat를 요리대에 |
| FishCooked | 45 | 15 | 1200 | 2 | |

- RawMeat, DeerMeat, FishRaw, Dandelion, Thistle은 Material이라 먹을 수 없다.

---

## 5. 전투

### 5.1 공격 [D]
- `public override bool StartAttack(Character target, bool secondaryAttack)` (Humanoid)
  - 플레이어에게 `target`은 쓰이지 않는다.
  - 실패 조건: `InAttack()`(연계 대기 중이면 예외), InDodge, `!CanMove`, 넉백, 비틀거림, InMinorAction, 무기 없음.
  - `Attack.Start`가 스태미나를 `HaveStamina(cost+0.1)`로 확인하고, 탄약을 확인하고, 트리거를 건다. 실제 휘두름은 →1.0.16 §G "공격 상태".
- 플레이어 입력(`PlayerAttackInput`, FixedUpdate): `m_attack`을 누르면 0.5초 동안 큐에 남는다. `m_attackHold`면 계속 다시 시도한다.
- 연계: `m_attackChainLevels`(Club·AxeStone 3 [A]). 같은 애니메이션이고 마지막 공격 뒤 0.2초 안이면 다음 단으로 간다. 마지막 단은 피해 ×2(`m_lastChainDamageMultiplier`).
- 스태미나: `m_attackStamina × (1+장비 보정) × SE − 33%×스킬`.
- 피해 배수: `GetRandomSkillFactor = Lerp(clamp01(k−0.15), clamp01(k+0.15), rand)`, `k = Lerp(0.4, 1, 스킬/100)`. 스킬 0이면 0.25~0.55다.

### 5.2 활 [D] + [A]
- 당기기: `m_attackHold`가 true인 첫 프레임에 `Attack.StartDraw`를 부른다. 탄약이 없으면 `$msg_outof $ammo_arrows`로 실패한다. 이후 `m_attackDrawTime += fixedDeltaTime`.
  - 막는 중, minor action, 무언가에 붙어 있으면 `drawTime = −1`로 취소된다.
- `public float GetAttackDrawPercentage()` = `clamp01(drawTime / Lerp(m_drawDurationMin, 0.2×min, 스킬))`.
  - 활 `m_drawDurationMin` = **2.5초** [A]. 스킬 100이면 0.5초다.
- 당기는 동안 스태미나: 초당 `m_drawStaminaDrain` 4 × (1 − 0.33×스킬) [A]. 다 당기면 절반이다.
- 발사: **hold가 false가 되는 프레임에** `drawTime > 0`이고 스태미나 > 0이면 `StartAttack(null, false)`를 부른다(당긴 비율 포함). 활 공격 자체의 스태미나는 0이다.
- 투사체(`FireProjectileBurst`)
  - 속도 = `Lerp(m_projectileVelMin 2, m_projectileVel 35 + 화살 보정 0, drawVelocityCurve(당긴 비율))` [A]
  - 흩어짐 = `Lerp(20°, 1°, sqrt(당긴 비율))`, yaw와 pitch를 무작위로 흩는다.
  - 피해 = `(활 + 화살) × 랜덤스킬계수 × 당긴 비율`. 화살 pierce: 나무 22, 부싯돌 27, 활 22 [A].
  - 조준 방향 = **`Humanoid.GetAimDir() = GetLookDir()`**(pitch 포함 시선, 카메라가 아님). Player는 이 메서드를 오버라이드하지 않는다.
  - 발사 위치 = 기준점 + up×1.5 + forward×1.0. 발사 시 몸이 시선 yaw로 돈다.
  - 화살 투사체(`bow_projectile`, `_flint`)는 gravity 5, ttl 20초 [A].
- 탄약은 자동 장착되고 한 발에 1개 쓴다. 활 내구도는 발사마다 −1이다.

### 5.3 막기 [D] + [A]
- `Player.SetControls(…, block, blockHold, …)`가 `m_blocking = blockHold`로 정한다.
  - **예외: 공용 PlayerPrefs `ToggleBlock`가 1이면 `block` 누름으로 토글된다**(봇이 사람 설정을 따라간다).
- `IsBlocking()` = `m_blocking && !InAttack && !InDodge && !InPlaceMode && !IsEncumbered && !InMinorAction && !IsStaggering`.
- `protected override bool BlockAttack(HitData hit, Character attacker)` (→1.0.16 §E)
  - 정면에서 온 공격만 막는다(`dot(hit.m_dir, forward) ≤ 0`). 막는 아이템은 왼손, 없으면 현재 무기다.
  - **패리** = `m_timedBlockBonus > 1`이고 막기를 시작한 뒤 0.25초 안. 막기 힘 = `base + base×스킬×0.5`이고 패리면 ×`m_timedBlockBonus`.
  - 스태미나: 패리면 `m_perfectBlockStaminaDrain`(0) [A], 아니면 `m_blockStaminaDrain`(10 [A]) × 막은 비율.
  - 스태미나가 남고 비틀거리지 않으면 피해를 줄이고 `DamageText Blocked`를 띄운다.
  - Blocking 스킬이 +1, 패리면 +2 오른다.
  - 패리하면 공격자의 `m_staggerWhenBlocked`(Eikthyr 1)에 따라 공격자를 비틀거리게 한다.

| 방패 [A] | 막기(+레벨당) | 패리 배수 | 튕겨냄 | 내구도 | 무게 | 이동 |
|---|---|---|---|---|---|---|
| ShieldWood | 6 (+6) | 1.5 | 20 | 200 (+50) | 4 | −5% |
| ShieldWoodTower | 10 (+6) | 0 (패리 불가) | 100 | 200 | 4 | −10% |

무기의 막기 힘은 Club·AxeStone 3(패리 2.0), SpearFlint 4, Bow 3이다.

### 5.4 회피, 점프, 달리기 [D] + [A]
- 회피가 나가는 입력: `SetControls(dodge:true)`, **막는 중 jump**(이동 방향이 없으면 뒤로), 웅크린 상태에서 jump. → `private void Dodge(Vector3)`: 0.5초 큐(과적이면 무시), Dodge 스킬 +0.1.
- `UpdateDodge`: 땅 위에 있고, 공격·과적·회피·비틀거림 중이 아니면 실행한다.
  - 스태미나 = `15 × (1 − 이동보정 + 회피보정) × SE × Lerp(1, 0.5, 스킬)` [A].
  - 회피 애니메이션 동안 무적(`IsDodgeInvincible`). 소음 5.
- 점프 10, 달리기 초당 8 × Lerp(1, 0.5, Run 스킬), 웅크려 걷기 초당 5, 과적 상태로 이동하면 초당 5 [A].

### 5.5 체력과 난이도 보정 [D] + [A]
- `public float GetHealthPercentage()` = `GetHealth() / GetMaxHealth()`.
- 생물의 최대 HP = `m_health × level`(`SetupMaxHealth`, level = 별 + 1). WorldLevel이 0이면 추가 배수는 없다.
- **인원 보정(1.0)**: HP는 바꾸지 않고 피해를 바꾼다.
  - `n = clamp(Player.GetPlayersInRangeXZ(대상 위치, m_difficultyScaleRange 100), 1, 5)`.
  - 플레이어가 아닌 대상이 받는 피해 × `1/(1 + (n−1)×0.3)`.
  - 플레이어가 아닌 공격자가 주는 피해 × `1 + (n−1)×0.04` [A].
  - 이 계산은 대상 소유자의 클라이언트에서, 그 클라이언트가 아는 플레이어 위치로 한다.
- 월드 수정자: `Game.m_playerDamageRate`, `m_enemyDamageRate`(전역 키 PlayerDamage, EnemyDamage ÷ 100)가 위에 곱해진다.
- **결과: 토르켈이 리더와 100m 안에 있으면 n = 2다.** 적이 받는 피해는 76.9%, 주는 피해는 104%가 된다.
  - **Eikthyr(500 HP)는 실질 650 HP**다.

---

## 6. 지각 동등성 [D] + [A]
| 대상 | 규칙 |
|---|---|
| `EnemyHud` | 기준점은 로컬 플레이어 위치. 일반 생물: **30m 안**이고 **최근 60초 안에 hover(조준)한 적이 있어야** 하고 화면 안에 있어야 한다(`m_hoverTimer` 초기값이 99999). 웅크린 플레이어는 숨긴다. 보스: **100m 안이고 `BaseAI.IsAlerted()`일 때만**(자는 Eikthyr는 HUD 없음). 이름은 `GetHoverName()`(번역됨), 별은 level 2·3 아이콘, 머리 위 표시는 `IsAlerted`면 alerted, `HaveTarget`면 aware. 체력 막대는 `GetHealthPercentage()`. 보스 HUD는 화면 위 고정이고 `public bool ShowingBossHud()`로 조회한다. |
| hover | `Player.FindHoverObject`(→1.0.16 §D). 덧붙일 점: **`BaseAI.IsSleeping()`인 생물과 안개에 가린 생물은 hover 생물이 되지 않는다.** 거리는 3.5 + `GetHoverOffset()` [A]. |
| `Hoverable` | `string GetHoverText()`, `string GetHoverName()`, `float GetHoverOffset()`. `Character.GetHoverName()`: Tameable → ZDO `s_overrideHoverName` → `Localize(m_name)`. `Character.GetHoverText()`는 길들인 생물이 아니면 "". |
| `Interactable` | `bool Interact(Humanoid user, bool hold, bool alt)`, `bool UseItem(Humanoid user, ItemDrop.ItemData item)`. |
| 이름 토큰 [A] | `$enemy_eikthyr`, `$enemy_deer`, `$enemy_boar`, `$enemy_neck`, `$enemy_greyling`, `$enemy_greydwarf`, `$enemy_greydwarfbrute`, `$enemy_greydwarfshaman` |
| `MessageHud`, `DamageText` | →1.0.16 §E (바뀐 것 없음) |
| 까마귀 | `Tutorial.ShowText` 계기(→1.0.16 §E): `Player.ShowTutorial("hammer"/"hoe"/"food"/"shield"/"boss_trophy"/"inventory"/"encumbered"/"death"/"cold"/"blackforest"/"haldor" …)`와, 전역 키·튜토리얼 연쇄로 10초마다 확인하는 `Tutorial.m_texts`. 여기에 로케이션 안의 고정 `GuidePoint`가 더해진다. StartTemple: `temple1`, `temple2`, `temple4`(`$tutorial_stemple*`). Eikthyrnir: 키 `Eikthyr` = `$tutorial_altar_topic/label/text` [A]. 코드 기본값으로 까마귀는 15m(`m_spawnDistance`) 안에 나타나 3m(`m_autoTalkDistance`)에서 말한다. 10m(`m_enemyCheckDistance`) 안에 적이 있거나 습격 중이면 숨는다(Ravens 프리팹 값은 확인하지 않음). |
| `RuneStone` | `public bool Interact(Humanoid character, bool hold, bool alt)`. `m_locationName`이 있으면 `Game.DiscoverClosestLocation`을 부른다. 랜덤 글이면 시드 `(int)x*(int)z`로 고른다. label이 있으면 `AddKnownText`(`$msg_newtext`), 그리고 `TextViewer.ShowText(Rune, topic, text, autoHide)`. 반환은 항상 false. hover는 `$piece_rune_read`. **TextViewer가 열려 있으면 TakeInput이 false다.** |
| `Vegvisir` | `public bool Interact(...)`: `m_locations`마다 `DiscoverClosestLocation(name, pos, pinName, pinType, showMap, discoverAll)`. 전역·플레이어 키를 설정할 수 있다. true를 돌려준다. hover는 `$piece_vegvisir $enemy_eikthyr [$KEY_Use] $piece_register_location`. |
| 위치 공개 | `Game.DiscoverClosestLocation` → 서버로 라우팅 RPC → `ZoneSystem.FindClosestLocation` → 보낸 사람에게 `RPC_DiscoverLocationResponse` → `Minimap.DiscoverLocation(pos, type, name, showMap)`. 새 핀이면 `$msg_pin_added: <name>`(TopLeft). 이미 있으면 `$msg_pin_exist`. showMap이면 **`ShowPointOnMap` → 큰 지도가 열린다**(`Minimap.IsOpen` → TakeInput false). 지도가 None 모드면 `SetLookDir`로 시선을 그쪽으로 3.5초 돌린다. |
| `ItemStand` (StartTemple 보스석) | `m_autoAttach=1`이고 지원 아이템이 1개다. **Use(Interact)로 인벤토리의 트로피를 건다**(없으면 `$piece_itemstand_missingitem`, 안 맞으면 `$piece_itemstand_cantattach`). 걸리면 `BossStone`이 `$guardianstone_trophyplaced`. 다시 Use하면 `$guardianstone_hook_power_activate`, 3초 뒤 `SetGuardianPower(m_guardianPower.name)` [A]. 이미 같은 힘이면 hover가 `$guardianstone_hook_alreadyactive`. 거치대에서 빼낼 수 없다(`m_canBeRemoved=0`). |
| 가디언 파워 | 버튼 `GP` → `public bool StartGuardianPower()`(애니메이션 `gpower`, 쿨다운 중이면 `$hud_powernotready`) → 애니메이션 이벤트 → `ActivateGuardianPower()`: 10m 안 모든 플레이어에게 SE를 준다. `GP_Eikthyr` [A]: 300초 동안 달리기·점프 스태미나 −60%, 쿨다운 1200초. |

---

## 7. 초원 생물 [A] + [D]

### 7.1 능력치
| 생물 | HP | 속도 걷기/달리기 | 피해 보정 | 공격 |
|---|---|---|---|---|
| Deer | 10 | 5/7 | spirit 면역 | 없음 |
| Boar | 10 | 5/8 | spirit 면역 | blunt 10, 범위 1.5, AI 2, 5초마다 |
| Neck | 5 | 5/5 | 불 약함, 독 저항 | slash 6, 범위 1.7 |
| Greyling | 20 | 5/4 | 불 매우 약함, 독 저항 | slash 5, 범위 1.5, AI 1.2, 2초마다 |
| Greydwarf | 40 | 5/6 | 불 매우 약함, 독 저항 | 근접 slash 14(범위 1.7, 2초마다), 돌 던지기 blunt 10(AI 사거리 5~15, 8초마다) |
| Greydwarf_Elite | 150 | 5/5 | 위와 같음 | slash 30, 범위 3 |
| Greydwarf_Shaman | 60 | 5/4 | 위와 같음 | 독 30 분사(범위 7), 아군 회복 |

- 모두 chop과 pickaxe 피해에 면역이다. 별: 최대 HP ×level, 드롭 확률·수량 ×2^(level−1)(→§0.4-4).

### 7.2 AI
| 생물 | AI | 시야(m/°) | 청각 | 경계 범위 | 도망 | 불 |
|---|---|---|---|---|---|---|
| Deer | AnimalAI | 25 / 45 | 15 | — | 감지하면 바로 `m_fleeRange` 25m로 도망. 경계가 풀리기까지 `m_timeToSafe` 15초. passiveAggressive. | 무서워함 |
| Boar | MonsterAI | 20 / 90 | 20 | 6 | `m_fleeIfNotAlerted`: 목표가 6m 밖이고 경계 전이면 도망. 맞으면 경계 → 공격. | 무서워함 |
| Neck | MonsterAI | 20 / 90 | 20 | 6 | Boar와 같음(물을 피하지 않음) | 무서워함 |
| Greyling, Greydwarf | MonsterAI | 30 / 90 | 9999 | 20 | 플레이어를 사냥하지 않음, 6초마다 맴돌기 | 피함(무서워하지 않음) |

- 감지 [D]: `BaseAI.CanSenseTarget` = 들음 또는 봄.
  - **들음**: 거리 ≤ `m_hearRange`이고 거리 < 대상 `GetNoiseRange()`.
  - **봄**: 거리 ≤ `m_viewRange × 대상 stealth`, 경계 전이면 시야각 안, 눈 사이 레이캐스트가 막히지 않음.
- 소음(`Character.AddNoise`, 초당 4m씩 줄어듦)
  - 걷기 15, 달리기 30, 점프 30, 웅크려 걷기 0, 회피 5
  - 공격 시작 `m_attackStartNoise`(기본 10), 맞힘 `m_attackHitNoise`(기본 30)
  - 건축·제거 50, **나무를 치면 10m 안의 가장 가까운 플레이어에게 100**
- stealth: 서 있으면 1이다. 웅크리면 `Lerp(0.5 + 빛×0.5, 0.2 + 빛×0.4, Sneak 스킬)`로 0.5초마다 다시 계산하고 초당 0.25씩 따라간다.
- AnimalAI: 대상이 정해지면(근처면 2초, 32m 밖이면 10초 주기로 `FindEnemy`) 바로 `Flee`(2초마다 반대쪽 ±45°로 25m 목표, 물은 피함).
  - 대상에게 `OnTargeted(false, false)`를 보낸다. sensed가 아니라서 침대 확인(`IsSensed`)을 막지 않는다.
- MonsterAI가 대상을 감지하면 `OnTargeted(sensed:true, …)`가 플레이어 `IsSensed()`를 1초 동안 켠다(→침대 `$msg_bedenemiesnearby`).
- 불: `m_afraidOfFire`인 동물은 3m 안 `EffectArea Fire`를 감지하면 6초 동안 경계하고 불에서 도망간다.

### 7.3 드롭 (`CharacterDrop`) [A]
| 생물 | 드롭 |
|---|---|
| Deer | DeerMeat 2, DeerHide 1~3, **TrophyDeer 50%**(레벨 배수, 개수 고정. pseudo 아님) |
| Boar | RawMeat 1, LeatherScraps 1, TrophyBoar 15%(pseudo) |
| Neck | NeckTail 70%, TrophyNeck 5%(pseudo) |
| Greyling | Resin 1 |
| Greydwarf | GreydwarfEye 50%, Stone 1, Wood 1, Resin 1, TrophyGreydwarf 5% |
| Eikthyr | TrophyEikthyr 1(100%), HardAntler 3(100%, `dontScale`) |

- `amountMin~Max`는 `Game.ScaleDrops`(자원 배율)를 적용한다. `m_levelMultiplier`면 수량 ×2^(level−1), NotAmount면 확률만 곱한다. 수량 상한은 100.

### 7.4 스폰 (`SpawnSystem`) [A] + [D]
| 항목 | 바이옴 | 최대/주기/확률 | 무리 | 시간 | 조건 |
|---|---|---|---|---|---|
| Deer | 초원+흑림 | 4 / 100초 / 50% | 1~3 | 밤낮 | 숲 안에서만, 레벨 1~3 |
| Boar | 초원 | 4 / 150초 / 50% | 1~3 | 밤낮 | 레벨 1~3(중심에서 800m 밖에서만 레벨업) |
| Neck(호수) | 초원 | 6 / 100초 / 50% | 2~4 | 밤낮 | 고도 −1.5~0.5 |
| Neck(비) | 초원 | 8 / 30초 / 100% | 2~4 | 밤낮 | Rain, LightRain, ThunderStorm |
| Greyling | 초원 | 2 / 300초 / 50% | 1 | 밤낮 | 숲 안 |
| **Greydwarf(초원)** | 초원 | 2 / 200초 / 50%, 1 / 120초 / 30%(숲) | 1, 2~3 | **밤만** | **`defeated_eikthyr` 필요** |
| Greydwarf(흑림) | 흑림 | 낮 3 / 120초 / 30%, **밤 6 / 60초 / 100%** | 2~3, 3~4 | | 키 없음 |

- 판정 [D]
  - 각 구역의 SpawnSystem을 **그 구역 소유자**가 1초마다 확인한다.
  - 후보 위치는 근처 플레이어 한 명을 골라 거기서 40~80m 떨어진 곳이다. **플레이어 40m 안은 제외**한다.
  - **PlayerBase EffectArea 안은 제외**한다(작업대 20m, 모닥불 25m).
  - 바이옴·숲·고도·기울기(≤35°)가 맞아야 한다.
  - 레벨업은 단계마다 10% 확률이다.
- 결론: Eikthyr 전 초원의 밤에는 그레이드워프가 초원에서 새로 생기지 않는다. **흑림 경계에서는 밤마다 3~4마리 무리가 생긴다.** 흑림 몹은 초원으로 넘어와 공격한다.
- 낮밤 [A]: 하루 1800초. 밤은 일 비율 ≥0.75 또는 ≤0.25(900초), 오후는 0.5~0.75.
- 기지 습격 `army_eikthyr`(멧돼지·넥 무리, 90초) [A]
  - `defeated_eikthyr`가 **없을 때** 일어날 수 있다.
  - 플레이어 근처의 PlayerBase 영역이 3개 이상이어야 한다(`baseValue ≥ 3`).
  - 46분마다 20% 확률이다.

---

## 8. Eikthyr

### 8.1 위치와 길 찾기 [A]
- 로케이션 `Eikthyrnir`
  - 월드당 3개, 우선 배치, 중심 1000m 안.
  - 외곽 반경 10, **건축 가능**(noBuild 0).
- 위치를 알아내는 방법
  1. **StartTemple 안의 `Vegvisir_Eikthyr`**(`$piece_vegvisir`)를 Use하면 가장 가까운 Eikthyrnir에 핀(`$enemy_eikthyr`, PinType Boss=9)이 생기고 **지도가 열린다**.
  2. Eikthyrnir의 `RuneTablet_Eikthyr`(`$piece_lorestone`, 글 `$lore_eikthyr`)를 읽어도 같은 핀이 생긴다(지도는 열리지 않음).
- 그 밖: 초원 룬스톤 `Runestone_Meadows`(월드당 100개, `$lore_meadows_random01~11`). `Runestone_Boars`(50개, 멧돼지 길들이기 글, 멧돼지 스포너 9개).
- StartTemple 보스석 `BossStone_Eikthyr`의 RuneStone 글은 `$guardianstone_eikthyr_desc`이고 위치를 알려주지 않는다. 트로피가 걸려 있으면 `m_dreamCinematic "Black Forest"`.

### 8.2 `OfferingBowl` [D] + Eikthyrnir 값 [A]
| 필드 | 코드 기본값 | `offeraltar_deer` [A] |
|---|---|---|
| `m_name` / `m_useItemText` | `$piece_offerbowl` / `$piece_offerbowl_offeritem` | `$piece_offerbowl_eikthyr` / 같음 |
| 메시지 | `m_usedAltarText $msg_offerdone`, `m_cantOfferText $msg_cantoffer`, `m_wrongOfferText $msg_offerwrong`, `m_incompleteOfferText $msg_incompleteoffering` | 같음 |
| `m_bossItem` / `m_bossItems` | null / 1 | **TrophyDeer / 2** |
| `m_bossPrefab` | null | Eikthyr |
| `m_spawnBossDelay` | 5 | **12** |
| `m_spawnBossMaxDistance` / `Min` / `MaxYDistance` | 40 / 0 / 9999 | **20 / 0 / 6** |
| `m_spawnYOffset` / `m_spawnPoints` | 1 / [] | 1 / [] (그릇 위치 기준 원 안에서 무작위) |
| `m_useItemStands` / `m_alertOnSpawn` / `m_setGlobalKey` | false / false / "" | false / false / "" |

- `public bool Interact(Humanoid user, bool hold, bool alt)`: `m_useItemStands`가 false면 **항상 false**다. Use 키로는 바칠 수 없다.
- `public bool UseItem(Humanoid user, ItemDrop.ItemData item)`: **hover한 채 단축바나 인벤토리 사용**(`UseItem(…, fromInventoryGui:false)`)으로 바친다.
  - 아이템 이름이 다르면 `$msg_offerwrong`(그래도 true를 돌려준다).
  - 개수가 모자라면 `"$msg_incompleteoffering: $item_trophy_deer n / 2"`.
  - 성공하면 `RPC_SpawnBoss`(그릇 ZNetView 소유자가 처리) → `CanSpawnBoss`(위치 100번 시도) → 12초 뒤 `DelayedSpawnBoss`.
  - 바친 사람에게 `RPC_BossSpawnInitiated`(`$msg_offerdone`)와 `RPC_RemoveBossSpawnInventoryItems`(트로피 2개 제거 + 제거 메시지)를 보낸다.
  - 이미 소환이 예약돼 있으면 아무 일 없이 true를 돌려준다.
- hover 글: `$piece_offerbowl_eikthyr\n[$KEY_HotbarUse] $piece_offerbowl_offeritem`.

### 8.3 Eikthyr [A] + [D]
- `$enemy_eikthyr`, faction Boss, `m_boss` 1, `m_bossEvent boss_eikthyr`, `m_defeatSetGlobalKey defeated_eikthyr`.
- **HP 500**, 속도 5/8, chop·pickaxe 면역. `m_staggerWhenBlocked` 1(패리하면 비틀거림).
- MonsterAI
  - 시야 40 / 90°, 청각·경계 9999
  - 플레이어 사냥 허용(`m_enableHuntPlayer` 1), 플레이어 구조물 공격, 공격 사이 최소 2초, 물을 피함
  - **`m_sleeping` 1, `m_wakeupRange` 5**
  - 소환 직후에는 잠든 상태다. 다음 경우에 깨어난다: 플레이어가 5m 안에 들어옴, 피해를 받음(`OnDamaged → Wakeup + 경계 + 공격자 타깃`), 사냥 모드.
  - 잠든 동안에는 보스 HUD도 hover도 없다.

| 공격 [A] | 피해 | 범위 / AI 사거리 | 주기 | 비고 |
|---|---|---|---|---|
| `Eikthyr_antler` | pierce 20 (+chop/pickaxe 1000 = 구조물 파괴) | 4.5 (각 25°) / 4 | 5초 | 막기·회피 가능 |
| `Eikthyr_charge` | lightning 15 | 20 (각 45°) / 15 | 25초 | 우선 사용, 막기·회피 가능 |
| `Eikthyr_stomp` | lightning 15, 범위형 | 3 / 6 | 40초 | 막기·회피 가능 |

- 처치하면 드롭: TrophyEikthyr(레벨 배수, 개수 1), HardAntler 3. 전역 키 `defeated_eikthyr`가 켜진다.
  - 그 결과 초원 그레이드워프 스폰과 `army_theelder` 습격 조건이 열리고, `army_eikthyr`는 꺼진다.
- 트로피를 처음 얻으면 튜토리얼 `boss_trophy`.
- 파워: StartTemple `BossStone_Eikthyr/itemstand`에 트로피를 Use로 걸고 → 다시 Use → 3초 → `GP_Eikthyr`(§6).

---

## 9. 채집 [D] + [A]
- `Pickable`: `public bool Interact(Humanoid character, bool repeat, bool alt)`
  - `m_enabled`, 타르를 확인한다(`$hud_itemstucktar`).
  - Foraging 같은 `m_pickRaiseSkill`이 있으면 스킬을 올리고, 보너스 확률은 스킬×0.25다.
  - → 소유자의 `RPC_Pick`: `m_amount`(ScaleDrops, 최소 `m_minAmountScaled`) + 보너스만큼 기준점 + up×0.5에 **위로 4m/s로 튕겨 떨군다** → `RPC_SetPicked`.
  - 반환값은 `m_useInteractAnimation`이다. hover 글은 `<이름>\n[$KEY_Use] $inventory_pickup`.
  - 떨어진 아이템은 자동 줍기(2m)로 들어온다.

| Pickable [A] | 주는 것 | 다시 자람(분) |
|---|---|---|
| Pickable_Branch (`$item_pickable_branch`) | Wood 1 | 240 |
| Pickable_Stone | Stone 1 | **0 = 다시 안 자람** |
| Pickable_Flint | Flint 1 | 240 |
| Pickable_Mushroom | Mushroom 1 | 240 |
| Pickable_Dandelion / Thistle | 1 | 240 |
| RaspberryBush / BlueberryBush | 1 | 300 |

- 나무·돌 피해 판정
  - `TreeBase`, `TreeLog`, `Destructible`, `MineRock(5)`는 모두 `private void RPC_Damage(long, HitData)`(소유자)에서 `hit.ApplyResistance(m_damageModifiers)` → `hit.CheckToolTier(m_minToolTier[, alwaysAllowTierZero])`를 한다. 실패하면 `DamageText TooHard`.
  - `CheckToolTier`: `hit.m_toolTier < m_minToolTier`면 false. `m_toolTier`는 `ItemData.m_shared.m_toolTier`다.
- 나무는 **chop 피해만 받는다**(나머지는 Immune [A]).

| 나무 [A] | HP / 필요 tier | 통나무 HP → 반쪽 | 반쪽 1개가 주는 것 | 그루터기 | 50% 보너스 |
|---|---|---|---|---|---|
| Beech1 | 80 / 0 | 60 → 2 × 60 | Wood 10 | Beech_Stub | Resin, Feathers, BeechSeeds |
| FirTree | 80 / 0 | 60 → 2 × 40 | Wood 10 | 100HP, Wood 2 | FirCone, Feathers, Resin |
| Pinetree_01 | 120 / 0 | 60 → 2 × 40 | Wood 또는 RoundLog 15 | 120HP, Wood 2 | |
| **Birch1/2** | 80 / **2** | tier 2 | Wood 또는 FineWood 10 | 80HP tier 2 | |
| **Oak1** | 200 / **2** | 160 → 140 | Wood 또는 FineWood 25 | 160HP tier 2 | Resin, Acorn, Feathers |

- 도구 tier [A]: AxeStone 0, **AxeFlint 1**, 그 밖의 초반 무기 0. **자작나무와 참나무는 부싯돌 도끼로도 안 된다**(청동 도끼 tier 2부터).
- 작은 나무 `Beech_small1/2`: Destructible, HP 20, 모든 물리 피해를 받는다. Wood·Resin 2~3.
- 바위 `Rock_3`, `rock1_mountain`, `rock4_coast`: Destructible, HP 1, **pickaxe 피해만**. 부서지면 MineRock5 조각(30~50HP, Stone 3~8)이 된다.
  - 초반에는 곡괭이가 없다. 돌은 Pickable_Stone과 그레이드워프 드롭으로 얻는다. 뿔 곡괭이는 Eikthyr의 HardAntler가 필요하다.
- 피해량: 한 번 휘둘러 여러 물체를 맞히면 `m_lowerDamagePerHit`로 나눠진다(→1.0.16 §G "피해 확인").

---

## 10. 요리와 불 [D] + [A]

### 10.1 `CookingStation` (`piece_cookingstation`, `$piece_cookingstation`)
- [A]
  - 슬롯 2개, `m_requireFire` 1, `m_fireCheckRadius` 0.25, 연료 없음, `m_canOvercookItems` 1.
  - 모든 변환이 **25초**다. **50초가 넘으면 Coal**(`m_overCookedItem`)이 된다.
  - 변환: RawMeat→CookedMeat, NeckTail→NeckTailGrilled, DeerMeat→CookedDeerMeat, FishRaw→FishCooked 외.
- `public bool UseItem(Humanoid user, ItemDrop.ItemData item)`, `public bool Interact(Humanoid user, bool hold, bool alt)`(hold면 false)
- 불 확인(`private bool IsFireLit()`): `m_fireCheckPoints`(없으면 자기 위치)마다 `EffectArea.IsPointInsideArea(p, Burning, 0.25)`다. **요리대를 모닥불 바로 위에 지어야 한다.**
- 실패 메시지: `$msg_needfire`, `$msg_nocookroom`, 요리할 것이 없으면 `$msg_nocookitems`, 맞지 않는 고기면 `<메시지> <아이템>`.
- Interact
  1. 다 익은 것(또는 탄 것)이 있으면 `RPC_RemoveDoneItem`이 **사용자 위치에 아이템을 만든다**(자동 줍기). Cooking 스킬 +0.6, 보너스 확률은 스킬×0.25.
  2. 없으면 인벤토리에서 첫 번째 요리 가능 아이템을 하나 올린다. 스킬 +0.4.
- 시간: 소유자가 ZDO의 `s_startTime`과의 차이로 진행한다. 불이 꺼져 있으면 멈춘다.
- hover 글: `$piece_cookingstation\n[$KEY_Use] $piece_cstand_cook\n[$KEY_HotbarUse] …`.

### 10.2 `Fireplace` (`fire_pit`, 조각 이름 `$piece_firepit`, Fireplace 이름 `$piece_fire`)
| 필드 | 코드 기본값 | fire_pit [A] |
|---|---|---|
| `m_startFuel` / `m_maxFuel` | 3 / 10 | **1** / 10 |
| `m_secPerFuel` | 3 | **5000** |
| `m_fuelItem` | — | Wood |
| `m_infiniteFuel` / `m_canTurnOff` / `m_canRefill` | false / false / true | false / false / true |
| EffectArea | — | PlayerBase 반경 25, Heat+Fire 반경 8, Burning 반경 0.45. 별도 Aoe가 불 피해 10을 1초마다 준다 |
| Piece | — | 비용 Stone 5 + Wood 2(Wood는 돌려받지 못함), comfort 1(Fire), **`m_notOnWood`** |

- `public bool Interact(Humanoid user, bool hold, bool alt)`
  - 인벤토리에 Wood가 있으면 1개를 넣는다(`$msg_fireadding`). 가득이면 `$msg_cantaddmore`, 없으면 `$msg_outof $item_wood`.
  - hold면 0.2초마다 반복한다.
- `public bool UseItem(Humanoid user, ItemDrop.ItemData item)`: 연료 아이템이면 같은 동작이다.
- `public void AddFuel(float)`도 있지만 치트·도구 경로라 봇은 쓰지 않는다.
- 연료: 소유자가 `시간/5000`만큼 줄인다. Wood 1개는 약 83분이다. hover 글에 `( $piece_fire_fuel n/10 )`이 보인다.
- `public bool IsBurning()` = `!m_blocked && 켜짐 && !물속 && fuel > 0`.
  - `m_blocked`(4초마다 확인): 지형이 불보다 0.2m 이상 높음, **불 위 0.5~1.0m에 단단한 물체**, 또는 연기가 4초 넘게 막힘(`SmokeSpawner`, 반경 0.5).
- **비는 불을 끄지 않는다.** 젖으면(`CheckWet`) 불꽃 모양만 낮아진다.
- 불 근처: Heat 타입 EffectArea(모닥불 8m)가 매 FixedUpdate 안에 있는 캐릭터의 `OnNearFire`를 부른다. 마지막 호출 뒤 0.25초 안이면 SE `CampFire`가 붙는다. Wet 남은 시간이 11배 빠르게 줄어든다(`SE_Wet`: `m_time += dt×10` 추가).

---

## 11. 생존 [D] + [A]

### 11.1 상태 효과와 휴식
| SE [A] | 지속 | 효과 |
|---|---|---|
| Resting (`SE_Cozy`) | `m_delay` **20초** 뒤 Rested를 건다 | HP 회복 ×3, 스태미나 회복 ×4. 시작 메시지 `$se_resting_start` |
| Rested (`SE_Rested`) | `m_baseTTL 480 + (편안함−1)×60`초 | HP ×1.5, 스태미나 ×2, 스킬 획득 +50%. 시작 `$se_rested_start ($se_rested_comfort:N)`, 끝 `$se_rested_stop` |
| Wet | 120초 | HP ×0.75, 스태미나 ×0.85. 불 근처에서 11배 빨리 마름 |
| Cold | 상태가 지속되는 동안 | HP ×0.5, 스태미나 ×0.75 |
| Shelter / CampFire | 상태가 지속되는 동안 | 표시만 함 |

- Resting 조건(`Player.UpdateEnvStatusEffects`, 매 프레임)
  - **`!IsSensed()`**
  - **(앉음 또는 InShelter)**
  - 추위·동결이 아님
  - 젖지 않음(WarmCozyArea는 예외)
  - Burning이 아님
  - **불 근처(CampFire)**
- Wet: 환경이 `m_isWet`이고 `!m_underRoof`(Player 중심 기준 `IsUnderRoof`)일 때 계속 갱신된다.
- Cold: 초원 밤이 `IsCold`면 불 근처가 아닐 때 Cold다.
- `Player.IsSensed()` = 마지막 `OnTargeted(sensed:true)` 뒤 1초 안. `IsTargeted()`는 아무 대상 지정이든 1초 안이다.

### 11.2 `Bed` [D] + [A]
- `public bool Interact(Humanoid human, bool repeat, bool alt)`
  1. **주인이 없는 침대**: `CheckExposure`를 통과하면 주인이 되고 스폰 지점으로 정한다(`$msg_spawnpointset`). 이때 잠들지는 않는다.
  2. **내 침대이고 현재 스폰 지점**이면 차례로 확인한다.
     - `EnvMan.CanSleep()`: 오후 또는 밤이고 기상 뒤 30초가 지남. 아니면 `$msg_cantsleep`.
     - `!IsSensed()`. 아니면 `$msg_bedenemiesnearby`.
     - 노출: underRoof가 아니면 `$msg_bedneedroof`, cover < 0.8이면 `$msg_bedtooexposed`.
     - **Heat 영역 안**. 아니면 `$msg_bednofire`.
     - 젖지 않음. 젖었으면 `$msg_bedwet`.
     - 통과하면 `AttachStart(…, isBed:true, "attach_bed")`.
  3. 내 침대지만 현재 스폰 지점이 아니면 노출만 확인하고 스폰 지점으로 정한다.
  - **남의 침대는 아무 일도 하지 않는다**(반환 false).
- 밤 넘기기(서버 `Game.UpdateSleeping`, 2초마다)
  - 조건: 오후 또는 밤, **모든 플레이어 캐릭터 ZDO의 `s_inBed`가 true**, 마지막 수면 뒤 10초.
  - → `SkipToMorning` → `SleepStart`. 깨면 `$msg_goodmorning` + Rested.
  - **봇도 자기 침대에 누워야 밤이 넘어간다.**
- `m_monsterCheckRadius` 20 [A]은 `Interact`에서 쓰이지 않는다.

### 11.3 죽음과 무덤 [D] + [A]
- `Player.OnDeath()`(소유자)
  - `s_dead`
  - `CreateTombStone()`: 기본 전역 키에서는 모든 장비를 풀고 인벤토리 전체를 무덤으로 옮긴다.
  - 음식 초기화
  - 마지막 죽음 뒤 `m_hardDeathCooldown` **600초**가 지났으면 스킬 −25%(`Skills.m_DeathLowerFactor` × `m_skillReductionRate`). 아니면 `$msg_softdeath`.
  - SE 제거, 10초 뒤 리스폰(침대 또는 사원)
  - `$msg_youdied`, 튜토리얼 `death`, 지도에 Death 핀 `$hud_mapday N`
- `TombStone.Interact(Humanoid, bool hold, bool alt)`
  - 비었으면 false다.
  - 주인이고 빈 칸이 충분하면 `Container.TakeAll` → `$piece_tombstone_recovered`.
  - 아니면 컨테이너 창을 연다(`InventoryGui.Show(container)`).
  - 회수하면 `m_lootStatusEffect`가 붙는다.

### 11.4 수리 [D]
- 아이템 수리
  - 스테이션 GUI의 `m_repairButton` → `private void OnRepairPressed()` → `private void RepairOneItem()`: **한 번 누를 때 하나만** 최대치로 고친다. `$msg_repaired`, Crafting 스킬 +(1−비율).
  - 고칠 것이 없으면 메시지 "No more item to repair"(번역 없음).
  - `Player.CanRepair`는 없다. `private bool InventoryGui.CanRepair(ItemDrop.ItemData)`
    - `m_canBeReparied`이고 레시피가 있어야 한다.
    - 레시피의 `m_repairStation` 또는 `m_craftingStation` 이름이 현재 스테이션과 같아야 한다.
    - `min(스테이션 레벨, 4) ≥ m_minStationLevel`이어야 한다.
  - 초반 [A]: Club, AxeStone, Hammer는 스테이션 없이 만들지만 **작업대에서 수리**한다. **Torch는 수리할 수 없다.**
- 건물 수리: 망치의 수리 조각 → `private void Repair(ItemData toolItem, Piece repairPiece)`(hover한 WearNTear).

---

## 12. 인벤토리 [D] + [A]
- 칸: `new Inventory("Inventory", null, 8, 4)`(`Humanoid.DefaultInventoryWidth/Height`). `Player.SetInventorySize(int rows)`는 0~9 줄까지 바꿀 수 있다.
- 무게
  - `GetTotalWeight()`가 `GetMaxCarryWeight()` = `m_maxCarryWeight` 300 × SE × `Game.m_carryWeightRate`를 넘으면 과적이다.
  - 과적이면 회피·스태미나 회복이 안 되고, 이동하면 초당 5를 쓰며, 튜토리얼 `encumbered`가 뜬다.
- `public bool CanAddItem(GameObject prefab, int stack = -1)` / `CanAddItem(ItemData item, int stack = -1)` = `FindFreeStackSpace(name, worldLevel) + 빈 칸 × m_maxStackSize ≥ stack`.
- `public ItemData AddItem(string name, int stack, int quality, int variant, long crafterID, string crafterName, bool cheated, bool pickedUp = false)`
  - 위치를 받는 오버로드에는 `dropIfFullInv = true`가 있다. 칸이 없으면 바닥에 떨어진다.
- 자동 줍기 2m(→1.0.16 §G).
- 스택 크기 [A]: Wood·Stone·Resin·LeatherScraps·DeerHide 50, **Flint 30**, RawMeat·DeerMeat·CookedMeat 20, 트로피 20, 화살 100.
- 무게 [A]: Wood·Stone·Flint 2, 트로피 2(Neck 0.5), Resin 0.3, LeatherScraps 0.5, DeerHide 1, 화살 0.1.
- 새 캐릭터는 **Torch와 ArmorRagsChest**를 가지고 시작한다(Player 기본 아이템 [A]).

## 13. 스킬 [D]
- `public void RaiseSkill(SkillType skillType, float factor = 1f)`(Skills). Player 쪽은 `public override void RaiseSkill(Skills.SkillType, float value = 1f)`이고 SE의 스킬 보정을 거친다.
- 누적치 += `m_increseStep(1) × factor × Game.m_skillGainRate`. 누적치가 `floor(level+1)^1.5 × 0.5 + 0.5` 이상이면 레벨 +1.
  - 메시지는 `$msg_skillup $skill_<name>: N`. 0레벨에서 처음 오를 때는 Center, 그 뒤로는 TopLeft다.
- `GetSkillFactor = level/100`. 죽으면(hard death) 모든 스킬이 25% 줄어든다.

---

## 14. 초반 레시피와 조각 [A]
- 모든 레시피는 활성화돼 있고, `m_requireOnlyOneIngredient` false, 정렬 가중치 100이다.
- 괄호는 품질이 1 오를 때 추가로 드는 양(`m_amountPerLevel`)이다.
- 여러 무기·방어구 레시피에 `Upgrader0Weapon`, `Upgrader1Weapon`, `Upgrader0Armor` ×1(업그레이더 자원)이 붙어 있다. 업그레이더 스테이션에서만 센다. 1.0.16도 같다.

| 아이템 | 수량 | 스테이션 | 재료 L1 (+레벨당) | 수리 | 최대 품질 |
|---|---|---|---|---|---|
| Club `$item_club` | 1 | **없음** | Wood 6; BoneFragments 0 (+5) | 작업대 | 4 |
| AxeStone `$item_axe_stone` | 1 | **없음** | Wood 5; Stone 4 (+2) | 작업대 | 4 |
| Hammer `$item_hammer` | 1 | **없음** | Wood 3 (+1); Stone 2 (+1) | 작업대 | 3 |
| Torch `$item_torch` | 1 | **없음** | Wood 1 (+1); Resin 1 (+1) | 불가 | 1 |
| Hoe | 1 | 작업대 1 | Wood 5 (+1); Stone 2 (+1) | | 3 |
| AxeFlint | 1 | 작업대 1 | Wood 4; Flint 6 (+3); LeatherScraps 0 (+2) | | 4 |
| KnifeFlint | 1 | 작업대 1 | Wood 2; Flint 4 (+2); LeatherScraps 2 | | 4 |
| SpearFlint | 1 | 작업대 1 | Wood 5 (+3); Flint 10 (+5); LeatherScraps 2 (+1) | | 4 |
| Bow (조잡한 활) | 1 | 작업대 1 | Wood 10 (+5); LeatherScraps 8 (+4); DeerHide 0 (+1) | | 4 |
| ArrowWood | **20** | 작업대 1 | Wood 8 | | |
| ArrowFlint | **20** | **작업대 2** | Wood 8; Flint 2; Feathers 2 | | |
| ShieldWood | 1 | 작업대 1 | Wood 10 (+5); Resin 4 (+2); LeatherScraps 4 (+2) | | |
| ShieldWoodTower | 1 | 작업대 1 | Wood 10 (+5); LeatherScraps 6 (+3) | | |
| ArmorRagsChest / Legs | 1 | 작업대 1 | LeatherScraps 5 (+5) | | 2 |
| ArmorLeatherChest / Legs, HelmetLeather | 1 | **작업대 2** | DeerHide 6 (+6); BoneFragments 0 (+5) | | 4 |
| CapeDeerHide | 1 | **작업대 2** | DeerHide 4 (+4); BoneFragments 5 (+5) | | 4 |

- 스테이션 없이 만들 수 있는 레시피(1.0.20 전체): AxeStone, Club, Hammer, Snowball, Torch.
- 무기·방어구 수치 [A]

| 아이템 | 스킬 / tier | 피해 (+레벨당) | 주 공격 스태미나 / 범위 | 보조 공격 | 내구도 | 무게 |
|---|---|---|---|---|---|---|
| Club | Clubs / 0 | blunt 12 (+6) | 6 / 2.4, 3연타 | 20 | 100 (+50) | 2 |
| AxeStone | Axes / 0 | slash 15, chop 20 (+5, +3) | 6 / 2.2, 3연타 | 12, ×1.5 | 100 (+30) | 1.5 |
| AxeFlint | Axes / **1** | slash 20, chop 30 (+5, +3) | 6 / 2.2 | 12 | 100 (+30) | 1.5 |
| KnifeFlint | Knives / 0 | slash 5, pierce 5 | 4 / 1.8 | 12, ×3 | 200 (+50) | 0.3 |
| SpearFlint | Spears / 0 | pierce 20 (+6) | 6 / 1.9 | 던지기 8(속도 20, 창 소모) | 100 (+50) | 1.5 |
| Bow | Bows / 0 | pierce 22 (+3) | 당기기 4/초, 2.5초 | — | 50 (+50) | 1.5 |
| Torch | Clubs | blunt 4, fire 15 | 4 | — | 20, 0.0333/초 | 1 |
| 맨손 `PlayerUnarmed` | Unarmed | blunt 5 | 주먹 4 / 1.5, 발차기 8 / 1.6 | | | |

| 방어구 [A] | 방어 (+레벨당) | 내구도 | 무게 | 장착 시간 |
|---|---|---|---|---|
| ArmorRagsChest / Legs | 1 (+1) | 200 | 2 | 2초 |
| ArmorLeatherChest / Legs | 2 (+2) | 400 | 5 | 2초 |
| HelmetLeather | 2 (+2) | 400 | 1 | 1초 |
| CapeDeerHide | 1 (+1) | 400 | 4 | 2초 |

| 조각 [A] | 이름 토큰 | 카테고리 | 비용 | 스테이션 | HP / 비고 |
|---|---|---|---|---|---|
| piece_workbench | `$piece_workbench` | Crafting | Wood 10 | 없음 | 200, 물·기울기(normal.y<0.8) 불가, 지붕 필요 |
| fire_pit | `$piece_firepit` | Misc | Stone 5, Wood 2 | 없음 | 100, **나무 위 불가** |
| piece_cookingstation | `$piece_cookingstation` | Crafting | Wood 2 | 없음 | 20 |
| woodwall | `$piece_woodwall` | BuildingWorkbench | Wood 2 | 작업대 | 400 |
| wood_wall_half | `$piece_woodwallhalf` | 〃 | Wood 1 | 작업대 | 400 |
| wood_floor | `$piece_woodfloor2x2` | 〃 | Wood 2 | 작업대 | 400 |
| wood_floor_1x1 | `$piece_woodfloor1x1` | 〃 | Wood 1 | 작업대 | 400 |
| wood_roof / wood_roof_45 / wood_roof_top | `$piece_woodroof26` / `45` / `top` | 〃 | Wood 2 | 작업대 | 400 |
| wood_wall_roof | `$piece_woodwallroof` | 〃 | Wood 2 | 작업대 | 400 |
| wood_beam / wood_stair | `$piece_woodbeam2` / `$piece_woodstair` | 〃 | Wood 2 | 작업대 | 400 |
| wood_door | `$piece_wooddoor` | 〃 | Wood 4 | 작업대 | 400 |
| bed | `$piece_bed` | Furniture | Wood 8 | 작업대 | 100, comfort 1(Bed) |
| piece_chest_wood | `$piece_chestwood` | Furniture | Wood 10 | 작업대 | 100, 5×2칸 |
| piece_workbench_ext1 | `$piece_workbench_ext1` | Crafting | Wood 10, Flint 10 | 작업대 | 작업대 레벨 +1 |
| piece_workbench_ext2 | `$piece_workbench_ext2` | Crafting | Wood 10, Flint 15, LeatherScraps 20, DeerHide 5 | 작업대 | 작업대 레벨 +1 |

- 조각은 모두 tier 0이고 바이옴·경작지 제한이 없다.
- 최소 은신처 예: 바닥 없이 woodwall 여러 장과 wood_roof로 cover ≥ 0.8을 만든다(17방향 레이 기준).
  - 작업대는 0.7, 침대는 0.8 이상이어야 한다.
  - 모닥불은 지붕 아래 0.5~1.0m에 막히지 않게 둔다. 연기 구멍이 없으면 연기가 막혀 4초 뒤 불이 꺼진다.

---

## 봇 구현 메모 (사람처럼 하는 방법과 함정)

공통 원칙
- 상호작용은 **hover와 같은 조건**으로 한다: 카메라 레이 + 눈에서 3.5m + hover offset. 경로는 →1.0.16 §D의 가상 `Use` 입력이나 private `Player.Interact` 리플렉션이다.
- 아이템 사용은 `Player.UseHotbarItem(i)`나 `Humanoid.UseItem(null, item, false)`로 한다.
- 진척은 **월드 변화로 확인**한다. 근거: 아래 Interact들은 성공해도 false를 돌려주는 경우가 많다(CraftingStation, RuneStone, OfferingBowl).

| 행동 | 사람과 같은 호출 순서 | 결과 검증 | 함정 |
|---|---|---|---|
| **제작** | 스테이션 루트에서 2m 안으로 이동 → 스테이션 hover → `Use` → `InventoryGui.IsVisible()`과 `GetCurrentCraftingStation() == 대상` 확인 → `m_availableRecipes`에서 `Recipe.m_item.name`이 같은 항목의 `InterfaceElement.GetComponent<Button>().onClick.Invoke()`(=`OnSelectedRecipe`) → `m_craftButton.interactable` 확인 → `m_craftButton.onClick.Invoke()`(=`OnCraftPressed`) → 2초 넘게(스킬 감소 반영) 기다림 | 인벤토리에서 결과 아이템이 `m_amount`만큼 늘고, 재료가 `GetAmount`만큼 줄어야 한다 | 대기 중 `Use`, `Inventory`, `Escape` 입력이 GUI를 닫아 취소된다. 2m 밖으로 밀려나도 GUI가 닫힌다. 지붕이 없거나 cover < 0.7이면 `$msg_stationneedroof` / `$msg_stationtooexposed`. 레시피 목록은 Show와 제작 후에만 다시 만들어진다(버튼 참조가 그때 바뀐다). 스테이션이 없는 레시피(돌도끼·몽둥이·망치·횃불)는 Tab 인벤토리(`InventoryGui.Show(null)`)에서 바로 만든다. 이때 시간 감소가 없다. |
| **레시피 해금 대기** | 재료를 줍거나(`$msg_newmaterial`) 작업대 4m 안에 들어가거나 직접 설치 → `$msg_newrecipe` / `$msg_newpiece` | `Player.IsRecipeKnown(name)` | 망치를 인벤토리에 가지고 있어야 조각이 해금된다. |
| **건축** | 망치를 장착(`UseHotbarItem`, 즉시) → `Player.SetSelectedPiece(piece)`(false면 아직 모르는 조각) → 회전은 `m_placeRotation`(휠과 같은 단위, 22.5°) → **시선(yaw·pitch)을 조절해 카메라 레이가 목표점을 맞히게** 함 → `GetPlacementStatus() == Valid` 대기 → 가상 `Attack` ButtonDown 한 프레임 | 반경 0.5m 안에 `Piece.GetCreator() == 내 PlayerID`인 새 조각이 생기고, 인벤토리 재료가 줄어야 한다 | `PlacePiece`와 `TryPlacePiece`를 직접 부르면 자원·스태미나·스킬 처리가 빠진다. 반드시 입력 경로를 쓴다. 레이는 카메라에서 나가고 거리 제한은 눈 기준 8m다. 3인칭 카메라 거리가 바뀌면 같은 시선이라도 맞는 점이 달라지므로 매번 `GetPlacementStatus`와 고스트 위치(`m_placementGhost`, private)를 확인한다. 자기 몸·리더와 겹치면 `$msg_blocked`. 모닥불은 땅이나 돌 위에만. 작업대는 평평한 땅(normal.y ≥ 0.8)에만. StartTemple 반경 25m 안은 지을 수 없다. 조각 선택창(`BuildMenu`)이 열려 있으면 설치되지 않는다. 0.4초 간격 제한. |
| **장착** | `UseHotbarItem(i)`. 단축바 밖 아이템은 인벤토리 GUI 경로(`InventoryGui`가 `UseItem(…, fromInventoryGui:true)`)를 쓴다 | `Humanoid.IsItemEquiped(item)` | 방어구는 2초 큐다. 그 사이 달리기·공격·회피를 하면 취소된다. hover 중인 Interactable이 `UseItem`을 먼저 가져간다. 예: 제물 그릇을 보고 있으면 `$msg_offerwrong`. |
| **먹기** | hover가 없는 상태에서 `UseHotbarItem` 또는 `UseItem(null, food, false)` | `GetFoods()`에 생기고 최대 HP·스태미나가 오름 | `CanEat`: 같은 음식은 반이 지나야 다시 먹을 수 있다. 3칸이 가득이면 `$msg_isfull`. 음식이 없으면 HP가 회복되지 않는다. 날고기는 먹을 수 없다. |
| **근접 공격** | `SetControls(attack:true)` 한 프레임 → `InAttack()` 시작을 확인(→1.0.16 §G) | 대상 HP 감소, `damage_dealt.on_target` | 연계는 0.2초 안에 다시 눌러야 한다. 스태미나는 cost+0.1보다 많아야 한다. 인원 보정으로 적이 받는 피해가 줄어든다(§5.5). |
| **활** | 활 장착 + 화살 → 시선(pitch 포함)으로 조준 → `SetControls(attackHold:true)`를 원하는 당김 시간 동안 유지 → hold false 한 프레임 | 화살 수 −1, 맞으면 대상 HP 감소 | 스킬 0이면 다 당기는 데 2.5초. 당긴 비율이 피해·속도·정확도에 곱해진다. 조준은 **카메라가 아니라 `GetLookDir`**이다. 막기(blockHold)가 당기기를 취소한다. 탄도는 중력 5, 최대 속도 35. 거리별 pitch 보정은 코드로 계산한다. |
| **막기, 패리, 회피** | 막기 = `SetControls(blockHold:true)`. 패리 = 맞기 0.25초 전 안에 막기 시작. 회피 = `SetControls(dodge:true)` 또는 막는 중 jump | 받은 피해(`m_onDamaged`)와 `DamageText Blocked` | 사람의 PlayerPrefs `ToggleBlock`가 1이면 의미가 토글로 바뀐다. 시작할 때 `PlayerPrefs.GetInt("ToggleBlock")`(읽기만)을 확인해 자기 입력 방식을 정한다. 타워실드는 패리가 안 된다. |
| **채집(Pickable)** | 대상 hover → `Use` | 인벤토리가 늘어남(아이템이 위로 튕겼다가 자동 줍기로 들어옴) | 줍는 데 1~2초 걸린다. Pickable_Stone은 다시 자라지 않는다. |
| **벌목** | 도끼 장착 → 서 있는 나무 → 휘두름 | 나무 HP(`s_health`) → 통나무 → 반쪽 통나무 → Wood 10~15 | 자작나무·참나무는 tier 2라 `TooHard`(부싯돌 도끼 tier 1로도 안 된다). 쓰러진 통나무가 굴러 사람을 친다(HitType Tree). 나무를 치면 가까운 플레이어에게 소음 100. |
| **요리** | 모닥불 위에 요리대를 지음 → 불 연료 확인(hover 글 n/10) → 요리대 hover → `UseHotbarItem(날고기)` 또는 `Use`(첫 요리 가능 아이템) → 25초 → `Use`로 꺼냄 | 익은 음식이 인벤토리에 들어옴(사용자 위치에 생겨 자동 줍기) | 50초가 넘으면 숯이 된다. 2칸. 불 판정은 Burning 영역 0.25m라 요리대가 불 바로 위에 있어야 한다. |
| **불 피우기·유지** | fire_pit 설치(시작 연료 1) → hover → `Use`(Wood 1개씩) | hover 글의 연료 수, `IsBurning()` | 연료 1개로 5000초. 비는 불을 끄지 않지만 머리 위가 막히면 꺼진다. |
| **휴식** | 은신처(cover ≥ 0.8 + 지붕) 안에서 불 8m 안 + 감지되지 않음 + 젖지 않음 → 20초 대기 | SE Resting → Rested(`$se_rested_start`) | 앉기(이모트)는 은신처가 없어도 된다. 젖어 있으면 Resting이 안 걸린다. |
| **잠** | 자기 침대를 지어 `Use`(스폰 지점 설정) → 오후·밤에 다시 `Use` | `InBed()`, 아침 `$msg_goodmorning` | 리더가 잘 때 **봇도 누워야 밤이 넘어간다**(모든 플레이어 `s_inBed`). 침대는 주인 전용이므로 봇은 자기 침대가 필요하다. 근처에 감지한 적이 있으면 `$msg_bedenemiesnearby`. 불 Heat 영역(8m) 안이어야 한다. |
| **Eikthyr 위치** | 사원 Vegvisir hover → `Use` → 큰 지도가 열림 → 지도 닫기(`Map` 입력 또는 `Minimap.SetMapMode(Small)`)를 사람처럼 | `Minimap` 핀(`$enemy_eikthyr`, Boss) 생성, `$msg_pin_added` | 지도가 열려 있는 동안 TakeInput이 false라 몸이 움직이지 않는다. 핀 좌표는 사람이 지도에서 보는 정보라 지각으로 넘겨도 된다. |
| **소환** | 사슴 트로피 2개 확보(사슴 50%, 별이면 100%) → 제물 그릇 hover(3.5m) → 트로피 단축바 키(=`UseItem(…, false)`) | `$msg_offerdone`, 트로피 −2, 12초 뒤 20m 안에 보스 생성 | Use(Interact)로는 바칠 수 없다. 트로피가 1개면 `$msg_incompleteoffering`. 소환된 Eikthyr는 **잠든 상태**이며 5m 접근이나 피해로 깬다. 첫 화살로 시작할 수 있다. 깨기 전에는 보스 HUD가 없다. |
| **보스전** | 패턴: 뿔(4m, 5초), 돌진 번개(15m, 25초), 발구르기(6m, 40초) | 보스 HP%(보스 HUD) | 실질 HP 650(2인 보정). 번개 피해에는 초반 방어구 저항이 없다. 패리하면 비틀거린다. 뿔 공격은 구조물 피해 1000이라 벽 뒤에 숨어도 안전하지 않다. |
| **파워** | 트로피를 줍고 → 사원 Eikthyr 보스석 거치대 hover → `Use`(자동 걸기) → 다시 `Use` → 3초 → `GP` 버튼 | `GetGuardianPowerName() == "GP_Eikthyr"`, 사용하면 SE | 쿨다운 1200초. 10m 안 아군 모두에게 적용된다. |
| **수리** | 작업대 GUI를 열고 `m_repairButton.onClick.Invoke()`를 아이템 수만큼 반복 | 내구도가 최대가 됨, `$msg_repaired` | 한 번에 하나만 고친다. 횃불은 수리할 수 없다. |
| **무덤** | 무덤 hover → `Use` | 인벤토리 복구, `$piece_tombstone_recovered` | 칸이 모자라면 컨테이너 창이 열리므로 GUI 경로로 옮긴다. 10분 안에 다시 죽으면 스킬 손실이 없다. |

나머지 함정 체크리스트
1. **1.0.20 대응이 먼저다.** 런타임 클론이 1.0.16(네트워크 40)이면 접속 단계에서 끝난다. 필요한 일:
   - 작업 트리에 있는 `tested-versions.json` 1.0.20 항목을 커밋한다.
   - 클론을 다시 만든다.
   - 1.0.16.md의 cheated 설명(§E 아래 "F 연관")을 갱신한다.
2. 거리 기준이 섞여 있다. 하나로 통일하지 않고 행동마다 게임 기준을 따른다.
   - hover와 상호작용: 눈 기준 3.5m
   - 건축: 눈 기준 8m
   - 작업대 사용: 루트 기준 2m
   - 스테이션 발견: 4m
   - 건축 범위: XZ 20m
   - 자동 줍기: 2m
3. 큰 지도(Vegvisir), TextViewer(룬스톤), InventoryGui(제작·상자·무덤)가 열려 있으면 `TakeInput`이 false다. 행동이 끝나면 닫는 것까지 스킬에 넣는다.
4. hover 대상이 `UseItem`을 가로챈다. 먹기와 장착은 hover를 비운 상태(하늘이나 땅을 보는 상태)에서 한다.
5. 인원 보정과 pseudo-random 드롭 카운터는 **생물 소유자 클라이언트** 기준이다. 봇이 소유자가 되면 봇의 프로필에 카운터가 저장된다. 봇 프로필 백업과 격리를 유지한다.
6. 밤 시간(900초)에 흑림 가장자리에 있으면 그레이드워프 무리(3~4마리)가 생긴다. 초원 한가운데, PlayerBase(작업대 20m, 불 25m) 안은 스폰이 없다.
7. `army_eikthyr` 습격은 PlayerBase 영역이 3개 이상인 기지 근처에서만 일어난다. 작업대와 모닥불을 한곳에 많이 두면 조건이 열린다.
8. 같은 Steam 계정이라 공용 PlayerPrefs(`ToggleBlock`, `mapenabled_<이름>`, 언어 등)를 봇이 함께 읽는다. 쓰기는 막는다(→1.0.16 §B3).
