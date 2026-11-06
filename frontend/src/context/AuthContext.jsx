import { createContext, useContext } from "react";

export const AuthContext = createContext(undefined);

export const useAuth = () => useContext(AuthContext);

