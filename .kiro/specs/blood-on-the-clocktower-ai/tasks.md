# Implementation Plan: Blood on the Clocktower AI

## Overview

This plan implements an AI-powered Blood on the Clocktower game with a Python/FastAPI backend, data-driven role definitions (YAML), LLM-powered AI agents, and a simple HTML/CSS/JS frontend. The implementation proceeds from data models and core engine outward to AI integration, API layer, and finally frontend.

## Tasks

- [x] 1. Set up project structure and data models
  - [x] 1.1 Create project directory structure and configuration files
    - Create the Python package structure: `game_engine/`, `ai_agents/`, `ai_agents/llm/`, `role_registry/`, `api/`, `models/`, `frontend/`, `data/roles/trouble_brewing/`, `data/scripts/`, `tests/property/`, `tests/unit/`, `tests/integration/`
    - Create `pyproject.toml` or `requirements.txt` with dependencies: fastapi, uvicorn, sse-starlette, pyyaml, pydantic, httpx, hypothesis, pytest
    - Create `__init__.py` files for all packages
    - _Requirements: 8.1_

  - [x] 1.2 Implement core data models
    - Create `models/game.py` with enums: `GamePhase`, `Team`, `RoleType`, `PlayerStatus`
    - Create dataclasses: `RoleDefinition`, `Player`, `Grimoire`, `GameSession`, `GameResult`
    - `Player` must include: `has_vote_token: bool = False` field (dead players receive one vote token upon death)
    - `Grimoire` must include: `about_to_die_player_id: Optional[str] = None`, `about_to_die_votes: int = 0`, `nominators_today: list[str]` (player_ids who have nominated today), `nominees_today: list[str]` (player_ids who have been nominated today)
    - Create `models/actions.py` with: `NightAction`, `NightActionResult`, `NightSummary`, `Message`, `Nomination`, `VoteContext`
    - Create `models/ai.py` with: `Personality`, `BeliefState`, `Claim`, `DiscussionContext`
    - _Requirements: 7.2, 10.1, 4.10, 4.5_

  - [x] 1.3 Create API request/response schemas
    - Create `api/schemas.py` with Pydantic models: `CreateGameRequest`, `CreateGameResponse`, `PlayerActionRequest`, `GameStateResponse`, `GameEvent`, `ScriptSummary`, `ScriptDetail`
    - Validate player_count is between 5 and 7 in `CreateGameRequest`
    - _Requirements: 10.4, 1.4_

  - [x] 1.4 Create game engine exceptions
    - Create `game_engine/exceptions.py` with: `InvalidPlayerCountError`, `ScriptNotFoundError`, `InvalidPhaseError`, `DeadPlayerActionError`, `InvalidTargetError`, `AbilityExhaustedError`, `NominationLimitError`
    - `NominationLimitError` raised when: a player has already nominated today, or a target has already been nominated today
    - _Requirements: 4.1_

- [x] 2. Implement Role Registry and data-driven role/script loading
  - [x] 2.1 Create YAML role definition files for Trouble Brewing
    - Create role files in `data/roles/trouble_brewing/`: `washerwoman.yaml`, `librarian.yaml`, `investigator.yaml`, `chef.yaml`, `empath.yaml`, `slayer.yaml`, `butler.yaml`, `poisoner.yaml`, `imp.yaml`
    - Each file includes: name, role_type, team, ability_description, first_night_order, other_nights_order, setup_requirements, information_provided, game_rules, night_action details
    - _Requirements: 7.1, 7.2, 7.7_

  - [x] 2.2 Create the Trouble Brewing script definition file
    - Create `data/scripts/trouble_brewing.yaml` with role lists per type, distribution table for player counts 5-7, and night order for first_night and other_nights
    - _Requirements: 7.3, 7.4, 7.7_

  - [x] 2.3 Implement the RoleRegistry class
    - Create `role_registry/registry.py` with `RoleRegistry` class
    - Implement `__init__` to load all role definition YAML files from data directory
    - Implement `get_role(role_name)` to retrieve a `RoleDefinition` by name
    - Implement `get_script(script_name)` to load and return a `Script` object
    - Implement `get_roles_for_player_count(script, player_count)` returning the distribution dict
    - Implement `select_roles(script, distribution)` to randomly select specific roles matching the distribution
    - Validate all required fields are present when loading role data, raise `RoleDataError` on malformed files
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.8, 8.2_

  - [x] 2.4 Write unit tests for RoleRegistry
    - Test `get_role` returns correct RoleDefinition for each Trouble Brewing role
    - Test `get_role` raises error for unknown role names
    - Test `get_script` loads Trouble Brewing with all 9 roles
    - Test `get_script` raises `ScriptNotFoundError` for unknown scripts
    - Test `get_roles_for_player_count` returns correct distribution for 5, 6, and 7 players
    - Test `select_roles` returns the right number of each role type
    - Test malformed YAML raises `RoleDataError` on load
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [x] 2.5 Write property test for Role Distribution Correctness (Property 1)
    - **Property 1: Role Distribution Correctness**
    - Test that for any valid script and player count (5-7), selected roles match the distribution table exactly with no duplicates and one role per player
    - **Validates: Requirements 1.2, 1.3, 7.4**

  - [x] 2.6 Write property test for Role Definition Completeness (Property 12)
    - **Property 12: Role Definition Completeness**
    - Test that every loaded role definition contains all required fields: name, role_type, team, ability_description, night action order, setup_requirements, information_provided, game_rules
    - **Validates: Requirements 7.2, 7.3**

  - [x] 2.7 Write property test for Script Role Containment (Property 13)
    - **Property 13: Script Role Containment**
    - Test that every role assigned in a game is a member of the script's role list
    - **Validates: Requirements 7.4**

- [ ] 3. Implement Game Engine core
  - [x] 3.1 Implement game creation and role assignment
    - Create `game_engine/engine.py` with `GameEngine` class
    - Implement `create_game(script_name, player_count, human_player_name)` that uses `RoleRegistry` to select and randomly assign roles
    - Create `Player` objects for the human player and AI agents
    - Initialize the `Grimoire` with all players, setting phase to SETUP
    - Distribute evil team knowledge CONDITIONALLY based on player count:
      - 7+ players: Minions learn Demon identity, Demon learns Minion identities + 3 Demon_Bluffs (not-in-play good characters from the script)
      - <7 players: No evil team knowledge distributed (no demon/minion info shared)
    - Demon `evil_knowledge` format (7+ players): `{"minion_ids": [...], "bluffs": ["Role1", "Role2", "Role3"]}`
    - Minion `evil_knowledge` format (7+ players): `{"demon_id": "..."}`
    - **NOTE: Previously completed but now needs rework due to conditional evil knowledge (7+ players only) and Demon Bluffs addition**
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

  - [x] 3.2 Write unit tests for game creation and role assignment
    - Test `create_game` produces correct player count for 5, 6, and 7
    - Test exactly one player is marked `is_human`
    - Test each player has a unique role assigned
    - Test role distribution matches the script's table for the given player count
    - Test with 7 players: Minion players receive Demon identity in their evil_knowledge
    - Test with 7 players: Demon player receives all Minion identities AND 3 Demon_Bluffs in their evil_knowledge
    - Test with 7 players: Demon_Bluffs are exactly 3 not-in-play good characters from the script
    - Test with 5 players: Minion players receive NO evil team knowledge
    - Test with 5 players: Demon player receives NO evil team knowledge (no minion_ids, no bluffs)
    - Test with 6 players: No evil team knowledge distributed
    - Test Townsfolk/Outsider players receive no evil team knowledge regardless of player count
    - Test invalid player count (4 or 8) raises `InvalidPlayerCountError`
    - Test invalid script name raises `ScriptNotFoundError`
    - **NOTE: Previously completed but now needs rework for conditional knowledge tests and bluffs**
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9_

  - [x] 3.3 Write property test for Conditional Evil Team Knowledge (Property 2)
    - **Property 2: Conditional Evil Team Knowledge**
    - Test that for games with 7+ players: every Minion knows the Demon's identity and the Demon knows all Minion identities
    - Test that for games with <7 players: NO evil team knowledge is distributed (Minions don't know Demon, Demon doesn't know Minions)
    - **NOTE: Previously completed but now needs rework — was "Evil Team Knowledge Symmetry", now conditional on player count**
    - **Validates: Requirements 1.6, 1.7, 1.8**

  - [x] 3.4 Write property test for Information Isolation (Property 3)
    - **Property 3: Information Isolation**
    - Test that no player can access another player's private role through the information system
    - **NOTE: Previously completed — verify it still passes with new evil_knowledge structure changes**
    - **Validates: Requirements 1.5, 2.2, 7.6**

  - [x] 3.5 Implement Night Phase processing
    - Implement `begin_night_phase(session)` to transition game to night, prepare night action queue
    - Implement `get_night_order(session, is_first_night)` to return ordered player_ids based on script night order, skipping dead players
    - Implement `resolve_night_action(session, player_id, action)` to process individual night actions and update state
    - Implement `complete_night_phase(session)` to finalize all night actions, compute deaths, produce `NightSummary`
    - When marking players as dead, grant them a `Vote_Token` (`has_vote_token = True`)
    - If the dying player is the Poisoner, immediately lift any active poison from the affected player
    - Handle: Demon kill marks target as dead, Poisoner sets target's is_poisoned flag, dead player actions are no-ops
    - _Requirements: 2.1, 2.3, 2.5, 2.6, 4.10, 11.5_

  - [x] 3.6 Implement first night information distribution
    - Implement `generate_info_for_role(session, player_id)` in a Storyteller helper
    - For Washerwoman: provide one Townsfolk player and one other player, one of whom is the specified role
    - For Librarian: provide one Outsider player and one other player, one of whom is the specified role
    - For Investigator: provide one Minion/Demon player and one other player
    - For Chef: provide count of evil pairs sitting next to each other
    - For Empath: provide count of alive evil neighbors
    - Handle poisoned players by providing potentially false information
    - _Requirements: 2.2, 2.4, 11.2_

  - [x] 3.7 Write unit tests for Night Phase
    - Test `begin_night_phase` transitions game phase to NIGHT
    - Test `get_night_order` returns correct order for first night vs other nights
    - Test `get_night_order` skips dead players
    - Test Demon kill marks target as DEAD
    - Test Demon kill grants target a Vote_Token (`has_vote_token = True`)
    - Test targeting a dead player has no effect
    - Test `complete_night_phase` returns NightSummary with dead player IDs only (no cause)
    - Test Washerwoman receives correct first-night info (two players, one of whom is a specific Townsfolk)
    - Test Librarian receives correct first-night info
    - Test Investigator receives correct first-night info
    - Test Chef receives correct evil-neighbor count
    - Test Empath receives correct alive-evil-neighbor count
    - **NOTE: Previously completed but needs addition of Vote_Token grant tests on death**
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 4.10_

  - [x] 3.8 Write property tests for Night Phase (Properties 4, 5, 6)
    - **Property 4: Night Order Preservation** — Test night abilities processed in script-defined order, skipping dead players
    - **Property 5: Demon Kill Resolution** — Test target dies after night resolution, summary reveals only identity
    - **Property 6: First Night Information Distribution** — Test info-gathering roles receive data on night 1
    - **Validates: Requirements 2.1, 2.3, 2.4, 2.6**

  - [x] 3.9 Implement Day Phase, Nomination, and Voting
    - Implement `begin_day_phase(session)` to transition game to day, reset daily state:
      - Reset `nominators_today` to empty list
      - Reset `nominees_today` to empty list
      - Reset `about_to_die_player_id` to None
      - Reset `about_to_die_votes` to 0
      - All players (alive and dead) may participate in discussion
    - Implement `nominate(session, nominator_id, target_id)` with validation:
      - Nominator must be alive
      - Nominator must NOT have already nominated today (check `nominators_today`)
      - Target must NOT have already been nominated today (check `nominees_today`)
      - Raise `NominationLimitError` when nomination limits are violated
      - Dead players cannot nominate (raise `DeadPlayerActionError`)
      - Track nominator in `nominators_today` and target in `nominees_today`
    - Implement `cast_vote(session, voter_id, nomination_id, vote)`:
      - Eligible voters: all alive players + dead players with `has_vote_token = True`
      - Dead players who vote have their token spent (`has_vote_token = False`) permanently
      - Dead players without token cannot vote (raise `DeadPlayerActionError`)
      - Butler voting restriction still applies
    - Implement `resolve_nomination(session, nomination_id)`:
      - Threshold: votes >= ceil(alive_count / 2)
      - If votes meet threshold AND exceed current `about_to_die_votes`: update `about_to_die_player_id` and `about_to_die_votes`
      - If votes meet threshold AND tie with current `about_to_die_votes`: clear `about_to_die_player_id` (no execution)
      - Does NOT execute immediately
    - Implement `end_day_phase(session)`:
      - Execute the `about_to_die_player_id` if set (mark as DEAD, grant Vote_Token)
      - If executed player is the Poisoner, immediately lift active poison
      - Return the executed player_id or None
      - Check win condition after execution
    - **NOTE: Previously completed but needs MAJOR rework for: nomination limits, vote tokens, about-to-die tracking, multiple nominations per day, execution at end of day, ceil threshold**
    - _Requirements: 3.1, 3.3, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9, 4.10, 4.11, 4.12, 14.2_

  - [ ] 3.10 Write unit tests for Day Phase, Nomination, and Voting
    - Test `begin_day_phase` transitions game phase to DAY and resets daily state (nominators_today, nominees_today, about_to_die)
    - Test all players (alive and dead) can send messages during discussion
    - Test `nominate` succeeds when nominator is alive and hasn't nominated today, target hasn't been nominated today
    - Test `nominate` rejects dead nominator with `DeadPlayerActionError`
    - Test `nominate` rejects when nominator already nominated today with `NominationLimitError`
    - Test `nominate` rejects when target already nominated today with `NominationLimitError`
    - Test `cast_vote` allows alive players to vote
    - Test `cast_vote` allows dead player with Vote_Token to vote (token is then spent)
    - Test `cast_vote` rejects dead player without Vote_Token with `DeadPlayerActionError`
    - Test `resolve_nomination` updates about_to_die when votes >= ceil(alive_count/2) and exceed current about_to_die_votes
    - Test `resolve_nomination` does NOT execute immediately (about_to_die is tracked, not killed)
    - Test `resolve_nomination` clears about_to_die on tie (equal qualifying votes)
    - Test multiple nominations per day allowed (not blocked after first success)
    - Test a later nomination with more votes replaces current about_to_die
    - Test `end_day_phase` executes about_to_die player
    - Test `end_day_phase` returns None when no about_to_die player
    - Test `end_day_phase` grants Vote_Token to executed player
    - Test `end_day_phase` lifts poison if executed player is the Poisoner
    - **NOTE: Previously completed but needs MAJOR rework for new mechanics**
    - _Requirements: 3.1, 3.3, 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.10, 4.11, 4.12_

  - [ ] 3.11 Write property tests for Day Phase and Voting (Properties 7, 8, 9, 21)
    - **Property 7: All Players Discussion Access** — All players (alive and dead) can send messages during day phase
    - **Property 8: Nomination Validity with Per-Day Limits** — Nomination accepted iff nominator alive, nominator hasn't nominated today, target hasn't been nominated today. Dead players cannot nominate.
    - **Property 9: Execution Threshold and About-To-Die Tracking** — Threshold is ceil(N/2), about_to_die tracked across multiple nominations, execution at end of day only, ties result in no execution
    - **Property 21: Vote Token Mechanics** — Dead players receive token on death, can use it once to vote, token spent permanently after use, rejected without token
    - **NOTE: Previously completed but needs MAJOR rewrite — Property 7 now includes dead players, Property 8 now has per-day limits, Property 9 completely changed to about-to-die + ceil threshold**
    - **Validates: Requirements 3.1, 3.3, 4.1, 4.3, 4.4, 4.5, 4.6, 4.7, 4.8, 4.10, 4.11, 4.12**

  - [ ]* 3.12 Write property test for Demon Bluffs (Property 22)
    - **Property 22: Demon Bluffs**
    - Test that for games with 7+ players, the Demon receives exactly 3 not-in-play good character names as bluffs
    - Each bluff must be a good-aligned role from the Script that is not assigned to any player in the game
    - For games with <7 players, no bluffs are distributed
    - **Validates: Requirements 1.9**

  - [ ] 3.13 Implement Win Condition Detection
    - Implement `check_win_condition(session)` that checks after each execution and night phase
    - Detect Good victory when Demon is executed
    - Detect Evil victory when only 2 living players remain and one is the Demon
    - Return `GameResult` with winning team, reason, and role reveals
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 3.14 Write unit tests for Win Condition Detection
    - Test Good wins when Demon is executed
    - Test Evil wins when 2 players remain and Demon is alive
    - Test no win when 3+ players remain
    - Test no win when Demon dies at night but 3+ players remain (Imp starpass scenario)
    - Test GameResult includes correct winning team, reason, and role reveals
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 3.15 Write property tests for Win Conditions (Properties 10, 11)
    - **Property 10: Good Victory on Demon Execution** — Demon executed → Good wins
    - **Property 11: Evil Victory at Two Players** — 2 alive with Demon → Evil wins
    - **Validates: Requirements 5.1, 5.2**

- [ ] 4. Implement special role mechanics
  - [ ] 4.1 Implement Poisoner night ability
    - In night phase processing, prompt Poisoner to select a target
    - Set `is_poisoned` on the target player; clear previous poison at start of each night
    - If Poisoner is dead, skip their action
    - Poisoned player's information-gathering abilities return potentially false results
    - When Poisoner dies (any cause — night kill, execution, Slayer), immediately lift active poison from affected player
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [ ] 4.2 Write unit tests for Poisoner
    - Test Poisoner can select a living target and that target becomes poisoned
    - Test previous poison is cleared at start of new night
    - Test dead Poisoner's action is skipped
    - Test poisoned Washerwoman receives potentially false info
    - Test poisoned Empath receives potentially incorrect count
    - Test Poisoner death (night kill) immediately lifts active poison from current target
    - Test Poisoner death (execution via end_day_phase) immediately lifts active poison
    - Test Poisoner death (Slayer shot) immediately lifts active poison
    - _Requirements: 11.1, 11.2, 11.3, 11.4, 11.5_

  - [ ]* 4.3 Write property tests for Poisoner (Properties 14, 15)
    - **Property 14: Poison Effect on Information** — Poisoned info-gathering roles get unreliable info
    - **Property 15: Poison Lifecycle Reset and Death Lift** — Poison cleared between consecutive nights AND poison lifts immediately on Poisoner death (any cause)
    - **Validates: Requirements 11.2, 11.3, 11.5**

  - [ ] 4.4 Implement Slayer day ability
    - Implement `use_day_ability(session, player_id, target_id)` for the Slayer
    - If target is the Demon, kill the Demon immediately and check win condition
    - If target is not the Demon, announce nothing happens
    - Mark ability as used (`used_ability = True`), reject further uses
    - If Slayer kills the Poisoner (if Poisoner is the Demon — edge case), lift poison
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [ ] 4.5 Write unit tests for Slayer
    - Test Slayer targeting Demon kills the Demon
    - Test Slayer targeting non-Demon announces nothing happens, target stays alive
    - Test Slayer ability marked as used after one use
    - Test second Slayer use is rejected with AbilityExhaustedError
    - Test Slayer kill triggers win condition check
    - _Requirements: 12.1, 12.2, 12.3, 12.4_

  - [ ]* 4.6 Write property test for Slayer (Property 16)
    - **Property 16: Slayer Ability Correctness**
    - Test Slayer kills Demon only, one-shot enforcement
    - **Validates: Requirements 12.1, 12.2, 12.3, 12.4**

  - [ ] 4.7 Implement Imp Starpass mechanic
    - In Demon kill resolution, detect self-targeting
    - If Imp targets self and living Minion exists: kill Imp, promote one living Minion to Imp role
    - If no living Minion exists: Imp simply dies (no promotion)
    - Update promoted player's role, abilities, and night order position
    - If Imp was also the Poisoner target (poisoned), clear poison since Poisoner's target died — but note: Imp dying doesn't affect Poisoner's poison status (only Poisoner death lifts poison)
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ] 4.8 Write unit tests for Imp Starpass
    - Test Imp self-targeting kills the Imp
    - Test Imp self-kill with living Minion promotes that Minion to Imp
    - Test promoted Minion has Imp role and abilities after starpass
    - Test Imp self-kill with no living Minion results in normal death, no promotion
    - Test starpass does not trigger Good victory (new Demon exists)
    - Test dead Imp receives Vote_Token on death
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ]* 4.9 Write property test for Imp Starpass (Property 17)
    - **Property 17: Imp Starpass Mechanic**
    - Test self-kill promotes exactly one Minion when available, no promotion otherwise
    - **Validates: Requirements 13.1, 13.2, 13.3**

  - [ ] 4.10 Implement Butler voting restriction and master selection
    - In night phase, prompt Butler to select a living player (not self) as master
    - Store master choice in Grimoire; reset each night
    - During voting, Butler may only vote in favor if their master also votes in favor
    - Reject self-selection as master with `InvalidTargetError`
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [ ] 4.11 Write unit tests for Butler
    - Test Butler can select a living player (not self) as master
    - Test Butler cannot select themselves as master
    - Test Butler's master choice resets each night
    - Test Butler can vote when master votes in favor
    - Test Butler cannot vote when master votes against
    - Test Butler vote restriction only applies to voting in favor (can always abstain)
    - _Requirements: 14.1, 14.2, 14.3, 14.4_

  - [ ]* 4.12 Write property tests for Butler (Properties 18, 19)
    - **Property 18: Butler Voting Restriction** — Butler votes only if master votes in favor
    - **Property 19: Butler Master Selection Validity** — Must be living, not self, reset nightly
    - **Validates: Requirements 14.1, 14.2, 14.3, 14.4**

- [ ] 5. Checkpoint - Ensure all engine tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Implement Storyteller orchestration
  - [ ] 6.1 Implement the Storyteller class
    - Create `game_engine/storyteller.py` with `Storyteller` class
    - Implement `run_night_phase(session)` that iterates night order, prompts AI agents (or human) for decisions, resolves actions, returns `NightSummary`
    - Implement `run_day_phase(session)` that manages discussion rounds (all players including dead can participate), allows multiple nominations, handles voting (including vote token logic), and calls `end_day_phase` at day's end
    - Coordinate with `AIAgentManager` for AI decisions and with API layer for human input
    - _Requirements: 2.1, 2.2, 3.1, 3.3, 4.1, 7.5, 8.2_

  - [ ]* 6.2 Write property test for Grimoire Completeness (Property 20)
    - **Property 20: Grimoire State Completeness**
    - Test that after any sequence of actions, the Grimoire contains all necessary state: players with status, current phase, messages, night deaths, about_to_die_player_id, about_to_die_votes, nominators_today, nominees_today, nomination history, and all other game state needed to reconstruct the game position
    - **Validates: Requirements 10.1**

- [ ] 7. Implement AI Agent system
  - [ ] 7.1 Implement LLM Provider interface and concrete providers
    - Create `ai_agents/llm/provider.py` with abstract `LLMProvider` class: `generate(prompt, system_prompt)` and `generate_structured(prompt, system_prompt, schema)`
    - Create `ai_agents/llm/openai_provider.py` implementing `OpenAIProvider`
    - Create `ai_agents/llm/anthropic_provider.py` implementing `AnthropicProvider`
    - Create `ai_agents/llm/local_provider.py` implementing `LocalProvider` (for Ollama or similar)
    - Include retry logic with exponential backoff and fallback handling for timeouts/errors
    - _Requirements: 8.4_

  - [ ] 7.2 Implement AIAgent class with personality and beliefs
    - Create `ai_agents/agent.py` with `AIAgent` class
    - Initialize with `Player`, `Personality`, and `LLMProvider`
    - Implement `BeliefState` management: tracking suspicions, known roles, claims, voting patterns
    - Implement `update_beliefs(observation)` to incorporate new information
    - Implement `get_claim_history()` to track public statements for consistency
    - Assign distinct personality traits that influence communication style and decision-making
    - _Requirements: 6.1, 6.2, 6.6_

  - [ ] 7.3 Implement AI Agent decision-making methods
    - Implement `decide_night_action(context)` to choose night targets based on role and strategy
    - Implement `generate_message(context)` to produce discussion messages accounting for role, beliefs, personality, and strategy
    - Implement `decide_vote(context)` to determine vote based on discussion context and suspicions
    - For Good roles: share truthful information with strategic timing
    - For Evil roles: fabricate believable false claims, coordinate with known evil team
    - Implement `decide_nomination(context)` to decide whether to nominate (considering per-day limit)
    - Implement fallback behavior when LLM is unavailable: random valid targets, skip messages, random votes
    - _Requirements: 6.2, 6.3, 6.4, 6.5, 3.2, 3.4, 4.9_

  - [ ] 7.4 Implement AIAgentManager
    - Create `ai_agents/manager.py` with `AIAgentManager` class
    - Implement `create_agents(session, ai_players)` to instantiate all AI agents with unique personalities
    - Implement `get_night_action(agent_id, context)` to prompt specific agent for night choice
    - Implement `generate_discussion_messages(agent_id, context)` to get discussion contributions
    - Implement `get_vote_decision(agent_id, context)` to get voting choices (accounting for vote tokens for dead AI players)
    - Implement `get_nomination_decision(agent_id, context)` to check if agent wants to nominate (only if alive and hasn't nominated today)
    - _Requirements: 3.2, 3.4, 3.5, 4.9, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 8. Implement REST API and SSE layer
  - [ ] 8.1 Implement FastAPI application and game endpoints
    - Create `api/routes.py` with FastAPI router
    - Implement `POST /game` to create a new game session, return game_id and human player info
    - Implement `GET /game/{game_id}` to return filtered game state for the human player
    - Implement `POST /game/{game_id}/action` to submit player actions (messages, votes, nominations, night choices, day abilities)
    - Implement `GET /scripts` and `GET /scripts/{script_name}` for script listing
    - Wire up error handling: 400 for invalid actions (including `NominationLimitError`), 403 for dead players without vote token, 404 for missing games, 409 for conflicts
    - _Requirements: 10.4, 8.5, 9.1_

  - [ ] 8.2 Write unit tests for API endpoints
    - Test `POST /game` creates a game and returns correct response schema
    - Test `POST /game` with invalid player count returns 400
    - Test `POST /game` with unknown script returns 404
    - Test `GET /game/{game_id}` returns filtered state (no other players' roles visible)
    - Test `GET /game/{game_id}` with unknown ID returns 404
    - Test `POST /game/{game_id}/action` with valid message action returns success
    - Test `POST /game/{game_id}/action` nomination from player who already nominated today returns 400
    - Test `POST /game/{game_id}/action` vote from dead player without token returns 403
    - Test `POST /game/{game_id}/action` with invalid action type returns 400
    - Test `GET /scripts` returns list of available scripts
    - _Requirements: 10.4, 8.5_

  - [ ] 8.3 Implement SSE event streaming
    - Implement `GET /game/{game_id}/events` as an SSE endpoint using `sse-starlette`
    - Create an event queue system that pushes game state changes to connected clients
    - Event types: `phase_change`, `message`, `nomination`, `vote`, `death`, `game_end`, `night_prompt`, `about_to_die_update`, `execution`
    - Maintain event queue per client for reconnection support
    - Push updates on all game state transitions: phase changes, new messages, deaths, votes, win conditions
    - _Requirements: 10.2, 10.3_

  - [ ] 8.4 Create the main application entry point
    - Create `main.py` that initializes FastAPI app, mounts static files for frontend, sets up CORS
    - Wire together: `RoleRegistry`, `GameEngine`, `Storyteller`, `AIAgentManager`, and API routes
    - Serve the frontend from a `/static` path or root
    - Provide a configuration mechanism for LLM provider selection (environment variables or config file)
    - _Requirements: 8.1, 8.4, 8.5_

- [ ] 9. Implement Frontend
  - [ ] 9.1 Create HTML structure and CSS styling
    - Create `frontend/index.html` with sections: game header (phase, day number), player list, message log, input area, role info panel
    - Create `frontend/styles.css` with responsive layout, distinct styling for alive/dead players, clear phase indicators, and readable message bubbles
    - Show vote token status for dead players
    - Ensure accessibility: semantic HTML, proper labels, contrast ratios
    - _Requirements: 9.1, 9.6_

  - [ ] 9.2 Implement JavaScript game client
    - Create `frontend/app.js` with game state management
    - Implement SSE connection with `EventSource` to receive real-time updates
    - Implement REST API calls for: creating games, submitting messages, casting votes, making nominations, using abilities, night choices
    - Render player list with alive/dead status indicators and vote token status
    - Render scrollable message log with sender names and timestamps (including messages from dead players)
    - Display human player's role, team, and any private info received
    - Show vote/nomination prompts with for/against buttons (disable vote if dead without token)
    - Show nomination prompt only if player hasn't nominated today
    - Show night ability prompts when applicable (target selection)
    - Display about_to_die status during day phase
    - On page refresh: fetch current state from `GET /game/{game_id}` and reconstruct UI
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 10.2, 10.3_

- [ ] 10. Checkpoint - Integration verification
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. End-to-end wiring and integration tests
  - [ ] 11.1 Wire the full game loop together
    - Connect Storyteller to AIAgentManager for automated AI turns
    - Implement the game loop: Setup → Night 1 → Day 1 (with multiple nominations, end_day_phase execution) → Night 2 → ... → Win condition
    - Ensure human player actions pause the loop and wait for input via API
    - Ensure SSE events fire at every state transition (including about_to_die updates)
    - Verify game can complete from start to end with mock LLM provider
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 5.2, 5.3, 10.1, 10.2_

  - [ ]* 11.2 Write integration tests
    - Test full game loop: create game → night 1 → day 1 (multiple nominations, end_day_phase) → night 2 → win condition
    - Test vote token lifecycle: player dies → receives token → uses token → cannot vote again
    - Test nomination limits: player nominates → cannot nominate again same day → can nominate next day
    - Test SSE event delivery on state changes
    - Test API contract: all endpoints return correct schemas
    - Test with mock LLM provider: AI agents produce valid structured responses
    - Test browser refresh state restoration
    - _Requirements: 10.2, 10.3, 10.4_

- [ ] 12. Final checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties from the design
- Unit tests validate specific examples and edge cases
- The LLM provider interface allows development/testing with a mock provider before connecting real LLM APIs
- All AI agent fallback behavior ensures games can progress even without LLM availability
- Previously completed tasks (3.1-3.4, 3.7, 3.9-3.11) are marked as not-started because the rules audit introduced significant mechanical changes that require reimplementation
- Key mechanical changes from rules audit: conditional evil knowledge (7+ only), Demon Bluffs, dead player discussion, Vote Tokens, nomination per-day limits, ceil threshold, about-to-die tracking with end-of-day execution, poison lift on Poisoner death

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "1.4", "2.1", "2.2"] },
    { "id": 2, "tasks": ["2.3"] },
    { "id": 3, "tasks": ["2.4", "2.5", "2.6", "2.7", "3.1"] },
    { "id": 4, "tasks": ["3.2", "3.3", "3.4", "3.5"] },
    { "id": 5, "tasks": ["3.6", "3.7", "3.8", "3.9"] },
    { "id": 6, "tasks": ["3.10", "3.11", "3.12", "3.13", "4.1", "4.4", "4.7", "4.10"] },
    { "id": 7, "tasks": ["3.14", "3.15", "4.2", "4.3", "4.5", "4.6", "4.8", "4.9", "4.11", "4.12"] },
    { "id": 8, "tasks": ["6.1"] },
    { "id": 9, "tasks": ["6.2", "7.1"] },
    { "id": 10, "tasks": ["7.2"] },
    { "id": 11, "tasks": ["7.3"] },
    { "id": 12, "tasks": ["7.4"] },
    { "id": 13, "tasks": ["8.1", "8.2", "8.3"] },
    { "id": 14, "tasks": ["8.4"] },
    { "id": 15, "tasks": ["9.1"] },
    { "id": 16, "tasks": ["9.2"] },
    { "id": 17, "tasks": ["11.1"] },
    { "id": 18, "tasks": ["11.2"] }
  ]
}
```
