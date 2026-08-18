# Requirements Document

## Introduction

This document defines the requirements for an AI-powered Blood on the Clocktower (BotC) game. A human player plays alongside AI agents, each embodying a specific character role with private information, personality, goals, and strategy. The system targets the Trouble Brewing edition with a limited subset of roles for the MVP, structured to support future expansion to additional roles and editions.

The game runs as a local web application with a Python/FastAPI backend, a simple web frontend, and a clean separation between game engine, AI/LLM integration, and UI layers.

## Glossary

- **Game_Engine**: The core module responsible for managing game state, enforcing rules, processing night actions, tracking alive/dead status, and advancing game phases
- **AI_Agent**: An LLM-powered player entity that reasons about the game, communicates with other players, and makes decisions according to its assigned role
- **Storyteller**: The automated game master that orchestrates the game flow, resolves night actions in correct order, and manages information distribution
- **Frontend**: The browser-based user interface that displays game state and allows the human player to interact with the game
- **Backend**: The FastAPI web server that connects the Frontend, Game_Engine, and AI_Agent systems
- **Human_Player**: The person playing the game through the browser interface
- **Night_Phase**: The phase where characters with night abilities act in a defined order, receiving or providing information privately
- **Day_Phase**: The phase where all players discuss, share information, accuse, and vote
- **Nomination**: The act of a living player formally accusing another player during the Day_Phase, triggering a vote. Each alive player may nominate at most once per day, and each player may be nominated at most once per day.
- **Execution**: The result of a successful nomination vote, removing a player from the game. A nominated player is executed if they received votes equal to at least half the number of alive players and more votes than any other nominated player that day.
- **Demon**: The evil team's primary role that kills one player each night
- **Minion**: An evil team member who supports the Demon through deception and misdirection
- **Townsfolk**: Good-aligned roles that gather information or have protective abilities
- **Outsider**: Good-aligned roles with abilities that may hinder the good team
- **Grimoire**: The complete game state including all role assignments, statuses, and night action results visible only to the Storyteller
- **Character_Sheet**: The private information available to a specific player, including their role, alignment, and any information received from night abilities
- **Role_Registry**: The extensible module that defines available character roles, their abilities, and their interaction rules
- **Script**: A named collection of character roles that defines what roles are available in a particular game. A game is created by providing a script. Trouble Brewing is the initial script for the MVP.
- **Role_Definition**: A structured data record describing a character role, including its ability, alignment/team, setup requirements, night action order, information the player receives, and relevant game rules
- **Edition**: A published collection of scripts and roles (e.g., Trouble Brewing, Sects & Violets, Bad Moon Rising). The MVP targets one edition but the architecture supports multiple.
- **Vote_Token**: A token given to dead players, allowing them one final vote for the rest of the game. Once used, it is spent and the player cannot vote again.
- **About_To_Die**: The nominated player who has received the most votes (at or above the execution threshold) during the current day. This player will be executed at end of day unless another player receives more votes.
- **Demon_Bluffs**: Three not-in-play good characters revealed to the Demon on the first night (in games of 7+ players) to help them create a believable cover story.

## Requirements

### Requirement 1: Game Setup and Role Assignment

**User Story:** As a player, I want the game to set up with a balanced set of roles assigned randomly from a provided script, so that each game is fair and unpredictable.

#### Acceptance Criteria

1. WHEN a new game is started, THE Game_Engine SHALL accept a Script and player count as input and create a game session
2. WHEN setting up the game, THE Game_Engine SHALL select roles from the Script according to the role distribution rules for the configured player count (number of Townsfolk, Outsiders, Minions, and Demons)
3. WHEN roles are selected, THE Game_Engine SHALL assign exactly one role to each player, including the Human_Player and all AI_Agents, randomly
4. WHEN a game is created, THE Game_Engine SHALL support a player count between 5 and 7 players for the MVP (1 human + 4-6 AI agents)
5. WHEN roles are assigned, THE Game_Engine SHALL provide each player only their own Role_Definition and alignment information as their initial Character_Sheet
6. WHERE there are 7 or more players in the game, WHEN roles are assigned, THE Game_Engine SHALL reveal to each Minion the identity of the Demon player
7. WHERE there are 7 or more players in the game, WHEN roles are assigned, THE Game_Engine SHALL reveal to the Demon the identities of all Minion players
8. WHERE there are fewer than 7 players in the game, THE Game_Engine SHALL NOT distribute evil team knowledge (Minions do not learn the Demon identity and the Demon does not learn Minion identities)
9. WHERE there are 7 or more players in the game, WHEN roles are assigned, THE Game_Engine SHALL reveal to the Demon three not-in-play good character names from the Script as Demon_Bluffs (safe bluff options that are not assigned to any player)

### Requirement 2: Night Phase Execution

**User Story:** As a player, I want night actions to resolve correctly and in the proper order, so that the game mechanics work as expected.

#### Acceptance Criteria

1. WHEN the Night_Phase begins, THE Game_Engine SHALL process night abilities in the order defined by the Trouble Brewing night order
2. WHEN a character with a night ability acts, THE Storyteller SHALL provide private information only to that character
3. WHEN the Demon selects a kill target during the Night_Phase, THE Game_Engine SHALL mark that player as dead unless a protective ability prevents it
4. WHEN the first night occurs, THE Game_Engine SHALL distribute starting information to roles that receive it (such as the Washerwoman, Librarian, Investigator, and Chef)
5. IF a night ability targets a dead player, THEN THE Game_Engine SHALL treat that action as having no effect
6. WHEN the Night_Phase completes, THE Game_Engine SHALL announce which players died during the night without revealing the cause

### Requirement 3: Day Phase Discussion

**User Story:** As a player, I want to discuss with other players during the day, so that I can gather information and identify evil players.

#### Acceptance Criteria

1. WHEN the Day_Phase begins, THE Game_Engine SHALL allow all players (both alive and dead) to communicate in a shared discussion
2. WHILE the Day_Phase is active, THE AI_Agent SHALL generate messages based on its role, private information, personality, and strategic goals
3. WHILE the Day_Phase is active, THE Human_Player SHALL be able to send messages visible to all players
4. WHILE the Day_Phase is active, THE AI_Agent SHALL respond to statements and questions from other players within the discussion context
5. WHEN an AI_Agent communicates, THE AI_Agent SHALL maintain consistency with its previously stated claims unless deliberately changing strategy

### Requirement 4: Nomination and Voting

**User Story:** As a player, I want to nominate suspects and vote on executions, so that the good team can eliminate evil players.

#### Acceptance Criteria

1. WHILE the Day_Phase is active, THE Game_Engine SHALL allow any living player to nominate another player for execution, subject to: only alive players may nominate, each alive player may nominate at most once per day, and each player (alive or dead) may be nominated at most once per day
2. WHEN a nomination is made, THE Game_Engine SHALL conduct a vote among all living players and any dead players who still possess their Vote_Token
3. WHEN a vote is conducted, THE Game_Engine SHALL require votes equal to at least half the number of alive players (rounded up for odd numbers) for the nomination to reach the execution threshold
4. WHEN a nominated player receives votes at or above the execution threshold AND receives more votes than any other nominee that day, THE Game_Engine SHALL mark that player as About_To_Die
5. THE Game_Engine SHALL allow multiple nominations per day, tracking each nominee's vote tally; if a new nominee receives more qualifying votes than the current About_To_Die player, the new nominee becomes About_To_Die instead
6. WHEN the Day_Phase ends, THE Game_Engine SHALL execute the About_To_Die player (if any), marking them as dead
7. THE Game_Engine SHALL allow at most one execution per day (at day's end)
8. IF two or more nominees are tied for the highest number of qualifying votes, THEN THE Game_Engine SHALL execute no one that day
9. WHEN an AI_Agent votes, THE AI_Agent SHALL decide its vote based on discussion context, suspicions, and strategic reasoning
10. WHEN a player dies, THE Game_Engine SHALL grant that player one Vote_Token
11. WHEN a dead player uses their Vote_Token to vote in a nomination, THE Game_Engine SHALL spend the token and prevent that player from voting in any future nominations
12. IF a dead player has already spent their Vote_Token, THEN THE Game_Engine SHALL prevent that player from voting

### Requirement 5: Win Condition Detection

**User Story:** As a player, I want the game to end when a win condition is met, so that there is a clear outcome.

#### Acceptance Criteria

1. WHEN the Demon is executed, THE Game_Engine SHALL declare a Good team victory and end the game
2. WHEN only two living players remain (including the Demon), THE Game_Engine SHALL declare an Evil team victory and end the game
3. WHEN a win condition is met, THE Frontend SHALL display the winning team, all role assignments, and a game summary

### Requirement 6: AI Agent Reasoning and Behavior

**User Story:** As a player, I want AI agents to behave like real players with believable reasoning and deception, so that the game feels engaging and challenging.

#### Acceptance Criteria

1. THE AI_Agent SHALL maintain an internal model of its suspicions and beliefs about other players' roles
2. WHEN reasoning about the game, THE AI_Agent SHALL consider its private information, public statements, voting patterns, and detected inconsistencies
3. WHILE assigned a Good role, THE AI_Agent SHALL attempt to identify evil players and share truthful information (with strategic timing)
4. WHILE assigned an Evil role, THE AI_Agent SHALL attempt to deceive other players by fabricating believable false claims
5. WHILE assigned an Evil role, THE AI_Agent SHALL coordinate with known evil team members to avoid contradicting each other
6. THE AI_Agent SHALL exhibit a distinct personality that influences its communication style and risk tolerance

### Requirement 7: Data-Driven Scripts and Role Definitions

**User Story:** As a developer, I want roles and scripts defined as structured data that the game engine loads and references, so that new characters and editions can be added without rewriting the engine.

#### Acceptance Criteria

1. THE Role_Registry SHALL load role definitions from structured data files (e.g., JSON or YAML) rather than hard-coding role behavior into the engine
2. EACH Role_Definition SHALL include at minimum: role name, alignment/team (Townsfolk, Outsider, Minion, Demon), ability description, setup requirements, night action order position, information the player receives, and relevant game rules
3. A Script SHALL be a named, ordered list of Role_Definitions that specifies which roles are available in a game
4. WHEN a new game is created, THE Game_Engine SHALL accept a Script as input and use it to determine available roles and role distribution rules
5. THE Storyteller SHALL have access to the complete Script and all Role_Definitions when managing the game
6. EACH AI_Agent SHALL have access only to the Role_Definition for its own assigned role and any information it would legitimately know in-game
7. THE MVP SHALL include the Trouble Brewing script containing the following roles: Washerwoman, Librarian, Investigator, Chef, Empath, Slayer (Townsfolk); Butler (Outsider); Poisoner (Minion); Imp (Demon)
8. THE architecture SHALL allow adding new roles by creating new Role_Definition data entries and adding new Scripts by composing existing Role_Definitions, without modifying the Game_Engine core

### Requirement 8: Extensible Architecture

**User Story:** As a developer, I want the architecture to be modular and extensible, so that future roles, editions, and features can be added without major refactoring.

#### Acceptance Criteria

1. THE Backend SHALL separate the Game_Engine, AI_Agent integration, and Frontend communication into independent modules
2. THE Game_Engine SHALL interpret Role_Definitions from data at runtime rather than relying on role-specific code paths for each character
3. THE Backend SHALL use Script definitions to configure games, specifying which roles are available and their distribution rules per player count
4. THE AI_Agent integration SHALL abstract the LLM provider behind an interface, allowing different models or providers to be substituted
5. THE Frontend SHALL communicate with the Backend exclusively through a REST API, enabling future frontend replacements
6. THE Game_Engine SHALL NOT contain hard-coded references to specific edition names or assume only one edition exists
7. NEW roles SHALL be addable by creating a Role_Definition data file and optionally implementing an ability handler if the role's mechanic is not expressible by existing handler patterns

### Requirement 9: Human Player Interface

**User Story:** As a human player, I want a clear and intuitive web interface, so that I can play the game without confusion.

#### Acceptance Criteria

1. THE Frontend SHALL display the current game phase (Night or Day), living and dead players, and the Human_Player's role information
2. WHEN the Day_Phase is active, THE Frontend SHALL provide a text input for the Human_Player to send messages to the discussion
3. WHEN a nomination occurs, THE Frontend SHALL present the Human_Player with a clear choice to vote for or against
4. WHEN the Night_Phase is active and the Human_Player has a night ability, THE Frontend SHALL prompt the Human_Player to make their choice
5. THE Frontend SHALL display a scrollable message log of all day discussion messages
6. THE Frontend SHALL use plain HTML, CSS, and JavaScript without requiring a complex frontend framework

### Requirement 10: Game State Persistence and Communication

**User Story:** As a player, I want the game state to be maintained reliably throughout the session, so that no information is lost.

#### Acceptance Criteria

1. THE Game_Engine SHALL maintain a complete Grimoire representing all game state throughout the session
2. WHEN the game state changes, THE Backend SHALL push updates to the Frontend in near real-time
3. IF the browser is refreshed, THEN THE Frontend SHALL restore the current game state from the Backend
4. THE Backend SHALL expose API endpoints for starting a new game, retrieving game state, submitting player actions, and receiving game events

### Requirement 11: Poisoner Night Ability

**User Story:** As the Poisoner player, I want to poison a player each night, so that their ability malfunctions.

#### Acceptance Criteria

1. WHEN the Night_Phase begins, THE Game_Engine SHALL prompt the Poisoner to select one living player to poison
2. WHILE a player is poisoned, THE Game_Engine SHALL cause that player's ability to malfunction (provide false information or have no effect)
3. WHEN a new Night_Phase begins, THE Game_Engine SHALL remove the previous poison before the Poisoner selects a new target
4. IF the Poisoner is dead, THEN THE Game_Engine SHALL skip the Poisoner's night action
5. IF the Poisoner dies (at any point during the game), THEN THE Game_Engine SHALL immediately lift any currently active poison from the affected player, ending the persistent poison effect upon the Poisoner's death

### Requirement 12: Slayer Day Ability

**User Story:** As the Slayer, I want to use my one-shot ability during the day to attempt to kill the Demon, so that I have an alternative way to win.

#### Acceptance Criteria

1. WHILE the Day_Phase is active, THE Game_Engine SHALL allow the Slayer to use their ability once per game to target a player
2. WHEN the Slayer targets the Demon, THE Game_Engine SHALL kill the Demon immediately
3. WHEN the Slayer targets a non-Demon player, THE Game_Engine SHALL announce that nothing happens
4. WHEN the Slayer ability has been used, THE Game_Engine SHALL prevent the Slayer from using it again

### Requirement 13: Imp Starpass Mechanic

**User Story:** As the Imp, I want the option to kill myself at night to pass the Demon role to a Minion, so that I can confuse the good team.

#### Acceptance Criteria

1. WHEN the Imp selects itself as the kill target during the Night_Phase, THE Game_Engine SHALL kill the Imp
2. WHEN the Imp kills itself, THE Game_Engine SHALL promote one living Minion to become the new Imp
3. WHEN a Minion is promoted to Imp, THE Game_Engine SHALL update that player's role and abilities to match the Imp role
4. IF no living Minion exists when the Imp kills itself, THEN THE Game_Engine SHALL treat the self-kill as a normal death with no promotion

### Requirement 14: Butler Voting Restriction

**User Story:** As the Butler, I want the game to enforce my voting restriction, so that the role's downside is properly implemented.

#### Acceptance Criteria

1. WHEN the Night_Phase begins, THE Game_Engine SHALL prompt the Butler to select one living player as their master
2. WHILE a vote is active, THE Game_Engine SHALL allow the Butler to vote only if the Butler's chosen master also votes in favor
3. WHEN a new Night_Phase begins, THE Game_Engine SHALL require the Butler to choose a new master
4. THE Game_Engine SHALL prevent the Butler from choosing themselves as their master
