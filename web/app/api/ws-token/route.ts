/**
 * API route to get the session token for WebSocket authentication.
 *
 * WebSocket connections can't send httpOnly cookies cross-origin,
 * so the frontend needs to fetch the token from this endpoint
 * and pass it as a query parameter.
 */

import { NextRequest, NextResponse } from "next/server";

export async function GET(request: NextRequest) {
  // Get the session token from cookies
  const token =
    request.cookies.get("next-auth.session-token")?.value ||
    request.cookies.get("__Secure-next-auth.session-token")?.value;

  if (!token) {
    return NextResponse.json(
      { error: "Not authenticated" },
      { status: 401 }
    );
  }

  // Return the token for WebSocket use
  return NextResponse.json({ token });
}
