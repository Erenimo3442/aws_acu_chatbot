import { postLogin, postRegister, postLogout, getWhoami } from '../lib/apiClient'
import type { AuthUser, LoginRequest, RegisterRequest } from '../types/api'

export async function login(credentials: LoginRequest): Promise<AuthUser> {
  const response = await postLogin(credentials)
  return response.user
}

export async function register(details: RegisterRequest): Promise<AuthUser> {
  const response = await postRegister(details)
  return response.user
}

export async function logout(): Promise<void> {
  await postLogout()
}

export async function whoami() {
  return getWhoami()
}
