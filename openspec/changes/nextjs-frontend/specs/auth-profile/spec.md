# Capability: Authentication, Session Hydration & Profile (`auth-profile`)

## ADDED Requirements

### Requirement: Session Hydration & Route Protection
The Next.js frontend SHALL hydrate user session state on mount via `GET /api/auth/session` and protect authenticated routes (`/dashboard`, `/investigation`, `/lab`, `/data`, `/reports`, `/profile`).

#### Scenario: Unauthenticated visitor opens a protected route
- **WHEN** `GET /api/auth/session` returns `{ authenticated: false, csrf_token: "..." }`
- **AND** the visitor navigates to `/dashboard`, `/investigation`, `/lab`, `/data`, `/reports`, or `/profile`
- **THEN** `AuthProvider` SHALL redirect to `/login?next=<encoded_path_and_query>`.

#### Scenario: Authenticated visitor opens login or register
- **WHEN** `GET /api/auth/session` returns `{ authenticated: true, user: { ... } }`
- **AND** the visitor navigates to `/login` or `/register`
- **THEN** `AuthProvider` SHALL redirect to `/dashboard`.

---

### Requirement: Registration, Sign-In & CSRF Rotation Sync
The `/login` and `/register` pages SHALL submit credentials to FastAPI with `X-CSRF-Token` and `credentials: "include"`, and synchronize rotated CSRF tokens immediately after login/registration.

#### Scenario: Valid registration or sign-in
- **WHEN** a user submits `/register` (`name` 2-60 chars, valid email, password 8-128 chars with letter + digit) or `/login`
- **THEN** `apiFetch()` sends `POST /api/auth/register` or `POST /api/auth/login` with `X-CSRF-Token`
- **AND** on `200 OK`, reads `csrf_token` and `user` from the response, updates the in-memory CSRF token, refreshes session stats, and navigates to `safeNext(res.next || "/dashboard")`.

#### Scenario: Rate-limited login after repeated failures
- **WHEN** 5 invalid password attempts occur for the same client IP (`X-Forwarded-For` or socket IP) and email within 300 seconds
- **THEN** FastAPI returns HTTP `429` with `"Too many failed attempts. Try again in X minute(s)."` and the login form displays the alert banner.

---

### Requirement: Profile Management, Avatar Crop & Gamification
The `/profile` page SHALL support editing user metadata, uploading/deleting avatars, changing passwords, displaying detective rank/badges, and deleting the account.

#### Scenario: Edit profile and change password
- **WHEN** the user submits `PUT /api/profile` (`name` 2-60, `job_title`/`company`/`location` <=80, `bio` <=300) or `POST /api/profile/password`
- **THEN** the UI updates the profile card and navbar identity immediately or displays validation errors (`403` wrong current password, `422` invalid input).

#### Scenario: Avatar upload and deletion
- **WHEN** the user drops or selects a PNG/JPEG/WEBP/GIF image (`<= 3 MB`)
- **THEN** `POST /api/profile/avatar` stores a 256x256 square-cropped PNG and updates `/avatar/me?v=<avatar_v>`; clicking Remove sends `DELETE /api/profile/avatar`.

#### Scenario: Delete account confirmation modal
- **WHEN** the user opens the Delete Account modal, enters their password, and confirms
- **THEN** `POST /api/profile/delete` deletes all user datasets, reports, avatar, notes, goals, and user record, clears `abd_dataset*` keys in `localStorage`, and navigates to `/`.
