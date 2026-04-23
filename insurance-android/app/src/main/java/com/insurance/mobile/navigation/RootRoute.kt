package com.insurance.mobile.navigation

/**
 * Root graph: startup → (server setup | login | main shell).
 *
 * Auth gating happens at this root level — the main graph below assumes a
 * live session, and anything under /api is rejected by the backend without
 * a valid Bearer token anyway.
 */
object RootRoute {
    const val Startup = "root/startup"
    const val ServerSetup = "root/server_setup"
    const val Login = "root/login"
    const val Main = "root/main"
}
