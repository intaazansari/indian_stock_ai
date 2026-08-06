import { apiClient } from "./client";
import type { User, AuthTokens } from "@/types/user";

export interface LoginPayload {
  email: string;
  password: string;
}

export interface RegisterPayload {
  email: string;
  password: string;
  full_name?: string;
}

export interface TokenResponse extends AuthTokens {
  token_type: string;
}

export const authApi = {
  login: async (payload: LoginPayload): Promise<TokenResponse> => {
    const { data } = await apiClient.post<TokenResponse>("/auth/login", payload);
    return data;
  },

  register: async (payload: RegisterPayload): Promise<User> => {
    const { data } = await apiClient.post<User>("/auth/register", payload);
    return data;
  },

  me: async (): Promise<User> => {
    const { data } = await apiClient.get<User>("/auth/me");
    return data;
  },

  refresh: async (refresh_token: string): Promise<TokenResponse> => {
    const { data } = await apiClient.post<TokenResponse>("/auth/refresh", { refresh_token });
    return data;
  },
};
