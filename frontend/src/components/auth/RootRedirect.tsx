import React from 'react';
import { Navigate } from 'react-router-dom';
import { isAuthed } from '../../lib/auth';

/**
 * Root redirect component that redirects to dashboard if authenticated,
 * otherwise to login. This ensures proper routing on initial load.
 */
export const RootRedirect: React.FC = () => {
  // Check auth state reactively
  const authenticated = isAuthed();
  
  // Always return valid JSX - Navigate component
  return <Navigate to={authenticated ? "/dashboard" : "/login"} replace />;
};

