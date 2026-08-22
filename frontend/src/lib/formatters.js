/**
 * Utility functions for formatting and calculating cricket analytics
 */

export const fmt = (value) => {
  try {
    return new Date(value).toLocaleString([], {
      weekday: 'short',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return 'Invalid date';
  }
};

/**
 * Format a price (odds) to 2 decimal places
 */
export const formatPrice = (price) => {
  if (!price) return '—';
  return Number(price).toFixed(2);
};

/**
 * Format probability as percentage
 */
export const formatProbability = (prob) => {
  if (prob === null || prob === undefined) return '—';
  return `${Math.round(prob * 100)}%`;
};

/**
 * SGM correlation boost calculation
 */
export const sgmCorrelationBoost = (legCount) => {
  if (legCount < 2) return 1;
  return Math.min(1.25, 1 + 0.05 * (legCount - 1));
};

/**
 * Calculate joint probability for multibets/SGM
 * @param {Array} legs - Array of leg objects with { probability, marketKey }
 * @param {boolean} correlated - Whether to apply correlation boost (true for SGM)
 */
export const calculateJointProbability = (legs, correlated = false) => {
  if (legs.length === 0) return 0;

  // Multiply probabilities (as decimals)
  const raw = legs.reduce((acc, leg) => acc * (leg.probability / 100), 1);

  // Apply correlation boost for SGM
  const boost = correlated ? sgmCorrelationBoost(legs.length) : 1;

  // Cap at 99% to avoid division issues
  return Math.min(0.99, raw * boost);
};

/**
 * Calculate implied decimal odds from probability
 */
export const calculateImpliedOdds = (probability) => {
  if (probability <= 0 || probability >= 1) return 0;
  return 1 / probability;
};

/**
 * Validate fixture ID
 */
export const isValidFixtureId = (fixtureId) => {
  return fixtureId && typeof fixtureId === 'string' && fixtureId.trim().length > 0;
};

/**
 * Validate market selection object
 */
export const isValidSelection = (selection) => {
  return (
    selection &&
    selection.key &&
    selection.name &&
    typeof selection.price === 'number' &&
    typeof selection.probability === 'number'
  );
};

/**
 * Truncate text to max length
 */
export const truncate = (text, maxLength = 50) => {
  if (!text) return '';
  return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
};
