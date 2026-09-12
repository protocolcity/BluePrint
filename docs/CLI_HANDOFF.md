# Run the BluePrint operations app

The active app serves Overview, Work, Projects and project papers, Agents, Activity, Map, Calendar, Connections, and Settings from one origin. WorkLane and WorkForce remain independent engines.

Use the canonical build, activation, verification, and recovery procedure in [DEPLOYMENT.md](operations/DEPLOYMENT.md).

Run `blueprint status --root /path/to/workspace` to identify the responding build. Development uses `blueprint serve --foreground --root /path/to/workspace --port 8893`; stop the preview after verification. Production activation normally serves localhost:8803. Do not create additional persistent UI services or use a second Homebrew update path.

The app refreshes verified local state and labels unavailable sources. GitHub activity is repository evidence; it is not remote agent liveness. Starting the app does not seed or hire agents.
