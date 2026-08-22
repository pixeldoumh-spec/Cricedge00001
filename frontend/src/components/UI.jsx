import React from 'react';
import { AlertCircle, Wifi } from 'lucide-react';

/**
 * Error display component
 */
export const ErrorBanner = ({ error, onDismiss }) => {
  if (!error) return null;

  return (
    <div className="error-banner" data-testid="error-banner" role="alert">
      <div className="error-content">
        {error.type === 'network_error' ? (
          <Wifi size={18} className="error-icon" />
        ) : (
          <AlertCircle size={18} className="error-icon" />
        )}
        <div className="error-text">
          <strong>{error.type === 'network_error' ? 'Connection Error' : 'Error'}</strong>
          <p>{error.message}</p>
        </div>
      </div>
      {onDismiss && (
        <button onClick={onDismiss} className="error-close" data-testid="error-dismiss">
          ×
        </button>
      )}
    </div>
  );
};

/**
 * Loading skeleton
 */
export const Skeleton = ({ width = '100%', height = '20px', ...props }) => (
  <div
    className="skeleton"
    style={{ width, height }}
    data-testid="skeleton"
    {...props}
  />
);

/**
 * Loading spinner
 */
export const LoadingSpinner = ({ text = 'Loading...' }) => (
  <div className="loading-spinner" data-testid="loading-spinner">
    <div className="spinner-ring"></div>
    <p>{text}</p>
  </div>
);

/**
 * Empty state
 */
export const EmptyState = ({ icon: Icon, title, description }) => (
  <div className="empty-state" data-testid="empty-state">
    {Icon && <Icon size={32} className="empty-icon" />}
    <h3>{title}</h3>
    <p>{description}</p>
  </div>
);
