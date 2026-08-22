import { useEffect, useState } from 'react';
import { fixturesAPI } from '@/lib/api';

/**
 * Hook to fetch and manage fixtures
 * @param {string} format - Optional format filter
 */
export const useFixtures = (format = null) => {
  const [fixtures, setFixtures] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      setLoading(true);
      setError(null);
      const result = await fixturesAPI.getFixtures(format);
      if (result.error) {
        setError(result.error);
      } else {
        setFixtures(result.data || []);
      }
      setLoading(false);
    };

    fetchData();
  }, [format]);

  return { fixtures, loading, error };
};

/**
 * Hook to fetch fixture formats
 */
export const useFixtureFormats = () => {
  const [formats, setFormats] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchFormats = async () => {
      const result = await fixturesAPI.getFormats();
      if (result.error) {
        setError(result.error);
      } else {
        setFormats(result.data?.formats || []);
        setTotal(result.data?.total || 0);
      }
      setLoading(false);
    };

    fetchFormats();
  }, []);

  return { formats, total, loading, error };
};

/**
 * Hook to fetch a single fixture
 * @param {string} fixtureId
 */
export const useFixture = (fixtureId) => {
  const [fixture, setFixture] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!fixtureId) {
      setLoading(false);
      return;
    }

    const fetchFixture = async () => {
      setLoading(true);
      const result = await fixturesAPI.getFixtureById(fixtureId);
      if (result.error) {
        setError(result.error);
      } else {
        setFixture(result.data);
      }
      setLoading(false);
    };

    fetchFixture();
  }, [fixtureId]);

  return { fixture, loading, error };
};

/**
 * Hook to fetch fixture predictions and markets
 * @param {string} fixtureId
 */
export const useFixtureMarkets = (fixtureId) => {
  const [predictions, setPredictions] = useState(null);
  const [markets, setMarkets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!fixtureId) {
      setMarkets([]);
      setLoading(false);
      return;
    }

    const fetchPredictions = async () => {
      setLoading(true);
      const result = await fixturesAPI.getFixturePredictions(fixtureId);
      if (result.error) {
        setError(result.error);
        setMarkets([]);
      } else {
        setPredictions(result.data);
        setMarkets(result.data?.markets || []);
      }
      setLoading(false);
    };

    fetchPredictions();
  }, [fixtureId]);

  return { predictions, markets, loading, error };
};

/**
 * Hook to manage portfolio state (SGM or Multibet)
 * @param {string} mode - 'SGM' or 'MULTI'
 */
export const usePortfolio = (mode) => {
  const storageKey = mode === 'SGM' ? 'ce.sgm.legs' : 'ce.multi.picks';

  const [legs, setLegs] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(storageKey)) || [];
    } catch {
      return [];
    }
  });

  useEffect(() => {
    localStorage.setItem(storageKey, JSON.stringify(legs));
  }, [legs, storageKey]);

  const addLeg = (leg) => {
    setLegs((prev) => [...prev, leg]);
  };

  const removeLeg = (legKey) => {
    setLegs((prev) => prev.filter((l) => l.key !== legKey));
  };

  const updateLeg = (legKey, updates) => {
    setLegs((prev) =>
      prev.map((l) => (l.key === legKey ? { ...l, ...updates } : l))
    );
  };

  const resetLegs = () => {
    setLegs([]);
  };

  return { legs, addLeg, removeLeg, updateLeg, resetLegs };
};
