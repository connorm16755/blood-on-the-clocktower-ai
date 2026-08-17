# Implementation Plan: Blood on the Clocktower AI

## Overview

This plan implements an AI-powered Blood on the Clocktower game with a Python/FastAPI backend, data-driven role definitions (YAML), LLM-powered AI agents, and a simple HTML/CSS/JS frontend. The implementation proceeds from data models and core engine outward to AI integration, API layer, and finally frontend.

## Tasks

- [ ] 1. Set up project structure and data models
  - [x] 1.1 Create project directory structure and configuration files
    - Create the Python package structure: `game_engine/`, `ai_agents/`, `ai_agents/llm/`, `role_registry/`, `api/`, `models/`, `frontend/`, `data/roles/trouble_brewing/`, `data/scripts/`, `tests/property/`, `tests/unit/`, `tests/integration/`
    - Create `pyproject.toml` or `requirements.txt` with dependencies: fastapi, uvicorn, sse-starlette, pyyaml, pydantic, httpx, hypothesis, pytest
    - Create `__init__.py` files for all packages
    - _Requirements: 8.1_

  - [-] 1.2 Implement core data models
    - Create `models/game.py` with enums: `GamePhase`, `Team`, `RoleType`, `PlayerStatus`
    - Create dataclasses: `RoleDefinition`, `Player`, `Grimoire`, `GameSession`, `GameResult`
    - Create `models/actions.py` with: `NightAction`, `NightActionResult`, `NightSummary`, `Message`, `Nomination`, `VoteContext`
    - Create `models/ai.py` with: `Personality`, `BeliefState`, `Claim`, `DiscussionContext`
    - _Requirements: 7.2, 10.1_

  - [x] 1.3 Create API request/response schemas
    - Create `api/schemas.py` with Pydantic models: `CreateGameRequest`, `CreateGameResponse`, `PlayerActionRequest`, `GameStateResponse`, `GameEvent`, `ScriptSummary`, `ScriptDetail`
    - Validate player_count is between 5 and 7 in `CreateGameRequest`
    - _Requirements: 10.4, 1.4_

- [ ] 2. Implement Role Registry and data-driven role/script loading
  - [ ] 2.1 Create YAML role definition files for Trouble Brewing
    - Create role files in `data/roles/trouble_brewing/`: `washerwoman.yaml`, `librarian.yaml`, `investigator.yaml`, `chef.yaml`, `empath.yaml`, `slayer.yaml`, `butler.yaml`, `poisoner.yaml`, `imp.yaml`
    - Each file includes: name, role_type, team, ability_description, first_night_order, other_nights_order, setup_requirements, information_provided, game_rules, night_action details
    - _Requirements: 7.1, 7.2, 7.7_

  - [ ] 2.2 Create the Trouble Brewing script definition file
    - Create `data/scripts/trouble_brewing.yaml` with role lists per type, distribution table for player counts 5-7, and night order for first_night and other_nights
    - _Requirements: 7.3, 7.4, 7.7_

  - [ ] 2.3 Implement the RoleRegistry class
    - Create `role_registry/registry.py` with `RoleRegistry` class
    - Implement `__init__` to load all role definition YAML files from data directory
    - Implement `get_role(role_name)` to retrieve a `RoleDefinition` by name
    - Implement `get_script(script_name)` to load and return a `Script` object
    - Implement `get_roles_for_player_count(script, player_count)` returning the distribution dict
    - Implement `select_roles(script, distribution)` to randomly select specific roles matching the distribution
    - Validate all required fields are present when loading role data, raise `RoleDataError` on malformed files
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.8, 8.2_

  - [ ] 2.4 Write unit tests for RoleRegistry
    - Test `get_role` returns correct RoleDefinition for each Trouble Brewing role
    - Test `get_role` raises error for unknown role names
    - Test `get_script` loads Trouble Brewing with all 9 roles
    - Test `get_script` raises `ScriptNotFoundError` for unknown scripts
    - Test `get_roles_for_player_count` returns correct distribution for 5, 6, and 7 players
    - Test `select_roles` returns the right number of each role type
    - Test malformed YAML raises `RoleDataError` on load
    - _Requirements: 7.1, 7.2, 7.3, 7.4_

  - [ ]* 2.5 Write property test for Role Distribution Correctness (Property 1)
    - **Property 1: Role Distribution Correctness**
    - Test that for any valid script and player count (5-7), selected roles match the distribution table exactly with no duplicates and one role per player
    - **Validates: Requirements 1.2, 1.3, 7.4**

  - [ ]* 2.5 Write property test for Role Definition Completeness (Property 12)
    - **Property 12: Role Definition Completeness**
    - Test that every loaded role definition contains all required fields: name, role_type, team, ability_description, night action order, setup_requirements, information_provided, game_rules
    - **Validates: Requirements 7.2, 7.3**

  - [ ]* 2.6 Write property test for Script Role Containment (Property 13)
    - **Property 13: Script Role Containment**
    - Test that every role assigned in a game is a member of the script's role list
    - **Validates: Requirements 7.4**

- [ ] 3. Implement Game Engine core
  - [ ] 3.1 Implement game creation and role assignment
    - Create `game_engine/engine.py` with `GameEngine` class
    - Implement `create_game(script_name, player_count, human_player_name)` that uses `RoleRegistry` to select and randomly assign roles
    - Create `Player` objects for the human player and AI agents
    - Initialize the `Grimoire` with all players, setting phase to SETUP
    - Distribute evil team knowledge: Minions learn Demon identity, Demon learns Minion identities
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ] 3.2 Write unit tests for game creation and role assignment
    - Test `create_game` produces correct player count for 5, 6, and 7
    - Test exactly one player is marked `is_human`
    - Test each player has a unique role assigned
    - Test role distribution matches the script's table for the given player count
    - Test Minion players receive Demon identity in their character sheet
    - Test Demon player receives all Minion identities in their character sheet
    - Test Townsfolk/Outsider players receive no evil team knowledge
    - Test invalid player count (4 or 8) raises `InvalidPlayerCountError`
    - Test invalid script name raises `ScriptNotFoundError`
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7_

  - [ ]* 3.3 Write property test for Evil Team Knowledge Symmetry (Property 2)
    - **Property 2: Evil Team Knowledge Symmetry**
    - Test that every Minion knows the Demon's identity and the Demon knows all Minion identities
    - **Validates: Requirements 1.6, 1.7**

  - [ ]* 3.3 Write property test for Information Isolation (Property 3)
    - **Property 3: Information Isolation**
    - Test that no player can access another player's private role through the information system
    - **Validates: Requirements 1.5, 2.2, 7.6**

  - [ ] 3.4 Implement Night Phase processing
    - Implement `begin_night_phase(session)` to transition game to night, prepare night action queue
    - Implement `get_night_order(session, is_first_night)` to return ordered player_ids based on script night order, skipping dead players
    - Implement `resolve_night_action(session, player_id, action)` to process individual night actions and update state
    - Implement `complete_night_phase(session)` to finalize all night actions, compute deaths, produce `NightSummary`
    - Handle: Demon kill marks target as dead, Poisoner sets target's is_poisoned flag, dead player actions are no-ops
    - _Requirements: 2.1, 2.3, 2.5, 2.6_

  - [ ] 3.5 Implement first night information distribution
    - Implement `generate_info_for_role(session, player_id)` in a Storyteller helper
    - For Washerwoman: provide one Townsfolk player and one other player, one of whom is the specified role
    - For Librarian: provide one Outsider player and one other player, one of whom is the specified role
    - For Investigator: provide one Minion/Demon player and one other player
    - For Chef: provide count of evil pairs sitting next to each other
    - For Empath: provide count of alive evil neighbors
    - Handle poisoned players by providing potentially false information
    - _Requirements: 2.2, 2.4, 11.2_

  - [ ] 3.6 Write unit tests for Night Phase
    - Test `begin_night_phase` transitions game phase to NIGHT
    - Test `get_night_order` returns correct order for first night vs other nights
    - Test `get_night_order` skips dead players
    - Test Demon kill marks target as DEAD
    - Test targeting a dead player has no effect
    - Test `complete_night_phase` returns NightSummary with dead player IDs only (no cause)
    - Test Washerwoman receives correct first-night info (two players, one of whom is a specific Townsfolk)
    - Test Librarian receives correct first-night info
    - Test Investigator receives correct first-night info
    - Test Chef receives correct evil-neighbor count
    - Test Empath receives correct alive-evil-neighbor count
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 2.6_

  - [ ]* 3.7 Write property tests for Night Phase (Properties 4, 5, 6)
    - **Property 4: Night Order Preservation** — Test night abilities processed in script-defined order, skipping dead players
    - **Property 5: Demon Kill Resolution** — Test target dies after night resolution, summary reveals only identity
    - **Property 6: First Night Information Distribution** — Test info-gathering roles receive data on night 1
    - **Validates: Requirements 2.1, 2.3, 2.4, 2.6**

  - [ ] 3.7 Implement Day Phase, Nomination, and Voting
    - Implement `begin_day_phase(session)` to transition game to day, reset daily state
    - Implement `nominate(session, nominator_id, target_id)` with validation: nominator alive, target alive, no execution yet today
    - Implement `cast_vote(session, voter_id, nomination_id, vote)` to record votes with Butler restriction enforcement
    - Implement `resolve_nomination(session, nomination_id)` to tally votes and execute if strict majority
    - Limit to one execution per day
    - _Requirements: 3.1, 4.1, 4.2, 4.3, 4.4, 4.5, 14.2_

  - [ ] 3.9 Write unit tests for Day Phase, Nomination, and Voting
    - Test `begin_day_phase` transitions game phase to DAY
    - Test `nominate` succeeds when nominator and target are alive, no execution yet
    - Test `nominate` rejects dead nominator
    - Test `nominate` rejects dead target
    - Test `nominate` rejects when execution already occurred today
    - Test `cast_vote` records for/against correctly
    - Test `resolve_nomination` executes target when votes > N/2
    - Test `resolve_nomination` does not execute when votes <= N/2
    - Test at most one execution per day (second successful nomination rejected)
    - _Requirements: 3.1, 4.1, 4.2, 4.3, 4.4, 4.5_

  - [ ]* 3.10 Write property tests for Day Phase and Voting (Properties 7, 8, 9)
    - **Property 7: Living Players Discussion Access** — Only living players can send messages
    - **Property 8: Nomination Validity** — Nomination accepted iff nominator alive, target alive, no execution today
    - **Property 9: Majority Vote Execution** — Execution iff votes > N/2
    - **Validates: Requirements 3.1, 4.1, 4.3, 4.4, 4.5**

  - [ ] 3.9 Implement Win Condition Detection
    - Implement `check_win_condition(session)` that checks after each execution and night phase
    - Detect Good victory when Demon is executed
    - Detect Evil victory when only 2 living players remain and one is the Demon
    - Return `GameResult` with winning team, reason, and role reveals
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ] 3.11 Write unit tests for Win Condition Detection
    - Test Good wins when Demon is executed
    - Test Evil wins when 2 players remain and Demon is alive
    - Test no win when 3+ players remain
    - Test no win when Demon dies at night but 3+ players remain (Imp starpass scenario)
    - Test GameResult includes correct winning team, reason, and role reveals
    - _Requirements: 5.1, 5.2, 5.3_

  - [ ]* 3.12 Write property tests for Win Conditions (Properties 10, 11)
    - **Property 10: Good Victory on Demon Execution** — Demon executed → Good wins
    - **Property 11: Evil Victory at Two Players** — 2 alive with Demon → Evil wins
    - **Validates: Requirements 5.1, 5.2**

- [ ] 4. Implement special role mechanics
  - [ ] 4.1 Implement Poisoner night ability
    - In night phase processing, prompt Poisoner to select a target
    - Set `is_poisoned` on the target player; clear previous poison at start of each night
    - If Poisoner is dead, skip their action
    - Poisoned player's information-gathering abilities return potentially false results
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [ ] 4.2 Write unit tests for Poisoner
    - Test Poisoner can select a living target and that target becomes poisoned
    - Test previous poison is cleared at start of new night
    - Test dead Poisoner's action is skipped
    - Test poisoned Washerwoman receives potentially false info
    - Test poisoned Empath receives potentially incorrect count
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

  - [ ]* 4.3 Write property tests for Poisoner (Properties 14, 15)
    - **Property 14: Poison Effect on Information** — Poisoned info-gathering roles get unreliable info
    - **Property 15: Poison Lifecycle Reset** — Poison cleared between consecutive nights
    - **Validates: Requirements 11.2, 11.3**

  - [ ] 4.3 Implement Slayer day ability
    - Implement `use_day_ability(session, player_id, target_id)` for the Slayer
    - If target is the Demon, kill the Demon immediately and check win condition
    - If target is not the Demon, announce nothing happens
    - Mark ability as used (`used_ability = True`), reject further uses
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

  - [ ] 4.5 Implement Imp Starpass mechanic
    - In Demon kill resolution, detect self-targeting
    - If Imp targets self and living Minion exists: kill Imp, promote one living Minion to Imp role
    - If no living Minion exists: Imp simply dies (no promotion)
    - Update promoted player's role, abilities, and night order position
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ] 4.8 Write unit tests for Imp Starpass
    - Test Imp self-targeting kills the Imp
    - Test Imp self-kill with living Minion promotes that Minion to Imp
    - Test promoted Minion has Imp role and abilities after starpass
    - Test Imp self-kill with no living Minion results in normal death, no promotion
    - Test starpass does not trigger Good victory (new Demon exists)
    - _Requirements: 13.1, 13.2, 13.3, 13.4_

  - [ ]* 4.9 Write property test for Imp Starpass (Property 17)
    - **Property 17: Imp Starpass Mechanic**
    - Test self-kill promotes exactly one Minion when available, no promotion otherwise
    - **Validates: Requirements 13.1, 13.2, 13.3**

  - [ ] 4.7 Implement Butler voting restriction and master selection
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
    - Implement `run_day_phase(session)` that manages discussion rounds, allows nominations, handles voting, and detects when day should end
    - Coordinate with `AIAgentManager` for AI decisions and with API layer for human input
    - _Requirements: 2.1, 2.2, 3.1, 4.1, 7.5, 8.2_

  - [ ]* 6.2 Write property test for Grimoire Completeness (Property 20)
    - **Property 20: Grimoire State Completeness**
    - Test that after any sequence of actions, the Grimoire contains all necessary state to reconstruct the game
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
    - Implement fallback behavior when LLM is unavailable: random valid targets, skip messages, random votes
    - _Requirements: 6.2, 6.3, 6.4, 6.5, 3.2, 3.4, 4.6_

  - [ ] 7.4 Implement AIAgentManager
    - Create `ai_agents/manager.py` with `AIAgentManager` class
    - Implement `create_agents(session, ai_players)` to instantiate all AI agents with unique personalities
    - Implement `get_night_action(agent_id, context)` to prompt specific agent for night choice
    - Implement `generate_discussion_messages(agent_id, context)` to get discussion contributions
    - Implement `get_vote_decision(agent_id, context)` to get voting choices
    - Implement `get_nomination_decision(agent_id, context)` to check if agent wants to nominate
    - _Requirements: 3.2, 3.4, 3.5, 4.6, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [ ] 8. Implement REST API and SSE layer
  - [ ] 8.1 Implement FastAPI application and game endpoints
    - Create `api/routes.py` with FastAPI router
    - Implement `POST /game` to create a new game session, return game_id and human player info
    - Implement `GET /game/{game_id}` to return filtered game state for the human player
    - Implement `POST /game/{game_id}/action` to submit player actions (messages, votes, nominations, night choices, day abilities)
    - Implement `GET /scripts` and `GET /scripts/{script_name}` for script listing
    - Wire up error handling: 400 for invalid actions, 403 for dead players, 404 for missing games, 409 for conflicts
    - _Requirements: 10.4, 8.5, 9.1_

  - [ ] 8.2 Write unit tests for API endpoints
    - Test `POST /game` creates a game and returns correct response schema
    - Test `POST /game` with invalid player count returns 400
    - Test `POST /game` with unknown script returns 404
    - Test `GET /game/{game_id}` returns filtered state (no other players' roles visible)
    - Test `GET /game/{game_id}` with unknown ID returns 404
    - Test `POST /game/{game_id}/action` with valid message action returns success
    - Test `POST /game/{game_id}/action` from dead player returns 403
    - Test `POST /game/{game_id}/action` with invalid action type returns 400
    - Test `GET /scripts` returns list of available scripts
    - _Requirements: 10.4, 8.5_

  - [ ] 8.3 Implement SSE event streaming
    - Implement `GET /game/{game_id}/events` as an SSE endpoint using `sse-starlette`
    - Create an event queue system that pushes game state changes to connected clients
    - Event types: `phase_change`, `message`, `nomination`, `vote`, `death`, `game_end`, `night_prompt`
    - Maintain event queue per client for reconnection support
    - Push updates on all game state transitions: phase changes, new messages, deaths, votes, win conditions
    - _Requirements: 10.2, 10.3_

  - [ ] 8.3 Create the main application entry point
    - Create `main.py` that initializes FastAPI app, mounts static files for frontend, sets up CORS
    - Wire together: `RoleRegistry`, `GameEngine`, `Storyteller`, `AIAgentManager`, and API routes
    - Serve the frontend from a `/static` path or root
    - Provide a configuration mechanism for LLM provider selection (environment variables or config file)
    - _Requirements: 8.1, 8.4, 8.5_

- [ ] 9. Implement Frontend
  - [ ] 9.1 Create HTML structure and CSS styling
    - Create `frontend/index.html` with sections: game header (phase, day number), player list, message log, input area, role info panel
    - Create `frontend/styles.css` with responsive layout, distinct styling for alive/dead players, clear phase indicators, and readable message bubbles
    - Ensure accessibility: semantic HTML, proper labels, contrast ratios
    - _Requirements: 9.1, 9.6_

  - [ ] 9.2 Implement JavaScript game client
    - Create `frontend/app.js` with game state management
    - Implement SSE connection with `EventSource` to receive real-time updates
    - Implement REST API calls for: creating games, submitting messages, casting votes, making nominations, using abilities, night choices
    - Render player list with alive/dead status indicators
    - Render scrollable message log with sender names and timestamps
    - Display human player's role, team, and any private info received
    - Show vote/nomination prompts with for/against buttons
    - Show night ability prompts when applicable (target selection)
    - On page refresh: fetch current state from `GET /game/{game_id}` and reconstruct UI
    - _Requirements: 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 10.2, 10.3_

- [ ] 10. Checkpoint - Integration verification
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 11. End-to-end wiring and integration tests
  - [ ] 11.1 Wire the full game loop together
    - Connect Storyteller to AIAgentManager for automated AI turns
    - Implement the game loop: Setup → Night 1 → Day 1 → Night 2 → ... → Win condition
    - Ensure human player actions pause the loop and wait for input via API
    - Ensure SSE events fire at every state transition
    - Verify game can complete from start to end with mock LLM provider
    - _Requirements: 1.1, 2.1, 3.1, 4.1, 5.1, 5.2, 5.3, 10.1, 10.2_

  - [ ]* 11.2 Write integration tests
    - Test full game loop: create game → night 1 → day 1 → night 2 → win condition
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

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1"] },
    { "id": 1, "tasks": ["1.2", "1.3", "2.1", "2.2"] },
    { "id": 2, "tasks": ["2.3"] },
    { "id": 3, "tasks": ["2.4", "2.5", "2.6", "2.7", "3.1"] },
    { "id": 4, "tasks": ["3.2", "3.3", "3.4", "3.5"] },
    { "id": 5, "tasks": ["3.6", "3.7", "3.8", "3.11"] },
    { "id": 6, "tasks": ["3.9", "3.10", "3.12", "4.1", "4.4", "4.7", "4.10"] },
    { "id": 7, "tasks": ["4.2", "4.3", "4.5", "4.6", "4.8", "4.9", "4.11", "4.12"] },
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
