# Technical Debt

Areas that work for the Trouble Brewing MVP but will need refactoring when expanding to additional editions, scripts, or larger player counts.

## 1. Butler Master Storage — Single Field

**Location:** `models/game.py` → `Grimoire.butler_master_id`

**Current:** A single `Optional[str]` field stores one Butler's master choice.

**Problem:** If a second edition adds another role with a "master" mechanic, or a homebrew script includes multiple Butlers, this field can't distinguish between them.

**Fix:** Replace with `master_selections: dict[str, str]` mapping `player_id → master_id`, keyed by the player who made the selection.

---

## 2. Win Condition Detection — Hard-Coded Logic

**Location:** `game_engine/engine.py` → `check_win_condition()`

**Current:** Two checks:
- Demon dead → Good wins
- 2 alive with Demon → Evil wins

**Problem:** Other editions have alternate or modified win conditions:
- Mastermind can delay Good's win by one day
- Zombuul requires dying twice before Good wins
- Al-Hadikhia has a player-choice death mechanic
- Some roles trigger draws or alternate evil win paths

**Fix:** Make win conditions pluggable per-script. Each script (or role) could register win condition modifiers that the engine evaluates in priority order.

---

## 3. Night Action Dispatch — if/elif Chain

**Location:** `game_engine/engine.py` → `resolve_night_action()`

**Current:** Dispatches on `action_type` string with if/elif ("kill", "poison", "choose_master").

**Problem:** Adding more action types (protect, learn, swap, redirect, etc.) will make this method increasingly long and hard to maintain.

**Fix:** Use a handler registry pattern:
```python
self._action_handlers: dict[str, Callable] = {
    "kill": self._handle_kill,
    "poison": self._handle_poison,
    "choose_master": self._handle_choose_master,
}
```
New roles register their action handlers at load time.

---

## 4. Imp Starpass — Role-Name Check

**Location:** Task 4.7 (upcoming implementation)

**Current/Expected:** Will likely check `role.name.lower() == "imp"` to detect self-kill starpass behavior.

**Problem:** Other Demons have different self-kill behaviors:
- Zombuul doesn't starpass (just registers a death)
- Fang Gu passes to an Outsider, not a Minion
- Al-Hadikhia has a choice-based death mechanic
- Some Demons simply die with no promotion

**Fix:** Add a `self_target_effect` field to `RoleDefinition` (already present in the YAML schema as `night_action.self_target_effect`). The engine should read this field rather than checking role names:
```python
if action.target_id == player_id and role.night_action.get("self_target_effect") == "starpass":
    ...
```

---

## 5. Single Demon / Single Minion Assumption

**Location:** Throughout `game_engine/engine.py` and `role_registry/registry.py`

**Current:** The distribution table and evil knowledge logic assumes exactly 1 Demon and 1 Minion for 5-7 player games.

**Problem:** Larger games (8-15 players) have multiple Minions. Some scripts introduce mechanics that temporarily create multiple Demons (e.g., Imp starpass creates a brief overlap). The Legion role is an entire team of Demons.

**Fix:**
- Evil knowledge distribution already handles lists (`minion_ids: [...]`), so it partially supports multiple Minions.
- The distribution table in `trouble_brewing.yaml` already specifies counts per role type — just needs larger player counts added.
- Win condition logic should check for "any living Demon" rather than assuming a single one (it already does this).
- Main gap: starpass promotion logic needs to handle the case where there are already multiple evil roles of various types.

---

## 6. Storyteller Info Generation — Hard-Coded Role Routing

**Location:** `game_engine/storyteller.py` → `generate_info_for_role()`

**Current:** An if/elif chain mapping role names to specific info generation functions.

**Problem:** Every new information-gathering role requires adding another branch and a new function pair (truthful + poisoned).

**Fix:** Make info generation data-driven. Each `RoleDefinition` could specify an `info_type` (e.g., "show_one_of_type", "count_evil_neighbours", "count_evil_pairs") and the engine dispatches to a generic handler parameterized by the role's data. Unusual roles that don't fit existing patterns would still need custom handlers, but the common patterns (show X of type Y) could be generalized.

---

## Priority

| Item | Impact | Effort | When to Address |
|------|--------|--------|-----------------|
| 3. Action dispatch | Medium | Low | Before adding 3+ new action types |
| 4. Starpass role check | Medium | Low | During task 4.7 implementation |
| 6. Info generation routing | Medium | Medium | Before adding 3+ new info roles |
| 2. Win conditions | High | Medium | Before adding Sects & Violets or BMR |
| 1. Butler master field | Low | Low | Before adding a second "master" role |
| 5. Multi-Demon/Minion | High | High | Before supporting 8+ player games |
