"""
Application services (use-case layer).

Services coordinate domain rules, repositories, and external adapters (e.g.
Google OAuth) behind cohesive operations. Routers call services; services call
repositories and domain helpers; domain modules depend on nothing.
"""
