import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { isAuthed } from '../../lib/auth';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

/**
 * Protected route component that redirects to login if not authenticated.
 * Always returns valid JSX - either the children or a Navigate component.
 */
export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const location = useLocation();
  const authenticated = isAuthed();

  // If not authenticated, redirect to login with return path
  if (!authenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Always return valid JSX - wrap children in fragment
  return <>{children}</>;
};

