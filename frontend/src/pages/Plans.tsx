import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Card } from '../components/common/Card';
import { PlanCard } from '../components/billing/PlanCard';
import { Loader } from '../components/common/Loader';
import { useLanguage } from '../context/LanguageContext';
import { getPlans } from '../lib/billingApi';
import { Plan } from '../types/plan';

/**
 * Standalone public pricing page.
 * No Sidebar, Topbar, or PageWrapper. Centered layout, max-w-6xl.
 */
export const Plans: React.FC = () => {
  const { direction, language, toggleLanguage, t } = useLanguage();
  const navigate = useNavigate();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchPlans = async () => {
      try {
        setLoading(true);
        setError(null);
        const data = await getPlans();
        setPlans(data.filter((plan) => plan.is_active));
      } catch (err: unknown) {
        const apiError = err as { message?: string };
        setError(
          apiError.message || t('error.generic')
        );
      } finally {
        setLoading(false);
      }
    };

    fetchPlans();
  }, [direction]);

  const handleSelectPlan = () => {
    // CTA: Get API Key / Contact Sales → go to login (or contact)
    navigate('/login');
  };

  const getRecommendedPlan = (): string | null => {
    const businessPlan = plans.find((p) =>
      p.name.toLowerCase().includes('business')
    );
    if (businessPlan) return businessPlan.name;
    if (plans.length >= 2) return plans[1].name;
    return null;
  };

  const recommendedPlanName = getRecommendedPlan();

  if (loading) {
    return (
      <div
        className="min-h-screen bg-slate-50 flex items-center justify-center px-4"
        dir={direction}
      >
        <Loader size="lg" />
      </div>
    );
  }

  return (
    <div
      className="min-h-screen bg-slate-50 flex flex-col"
      dir={direction}
    >
      {/* Minimal top: logo + language + log in */}
      <header className="w-full max-w-6xl mx-auto px-4 sm:px-6 pt-6 pb-4 flex items-center justify-between">
        <Link
          to="/"
          className="text-xl font-bold text-slate-900 hover:text-emerald-600 transition-colors"
        >
          ZATCA
        </Link>
        <div className="flex items-center gap-3">
          <button
            onClick={toggleLanguage}
            className="text-sm font-medium text-slate-600 hover:text-slate-900 px-3 py-1.5 rounded-lg hover:bg-slate-100 transition-colors"
          >
            {language === 'en' ? 'العربية' : 'English'}
          </button>
          <Link
            to="/login"
            className="text-sm font-medium text-emerald-600 hover:text-emerald-700"
          >
            {t('login.title')}
          </Link>
        </div>
      </header>

      {/* Main content: centered, max-w-6xl */}
      <main className="flex-1 w-full max-w-6xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {error ? (
          <Card padding="lg" className="max-w-md mx-auto">
            <div className="text-center py-8">
              <p className="text-red-600 mb-4">{error}</p>
              <button
                onClick={() => window.location.reload()}
                className="text-emerald-600 hover:text-emerald-700 font-medium"
              >
                {t('common.retry')}
              </button>
            </div>
          </Card>
        ) : (
          <div className="space-y-10 sm:space-y-12">
            {/* Heading */}
            <div className="text-center">
              <h1 className="text-3xl sm:text-4xl font-bold text-slate-900 mb-2">
                {t('plans.title')}
              </h1>
              <p className="text-slate-600 text-base sm:text-lg max-w-2xl mx-auto">
                {t('plans.subtitle')}
              </p>
            </div>

            {/* Pricing cards */}
            {plans.length === 0 ? (
              <Card padding="lg" className="max-w-md mx-auto">
                <div className="text-center py-8">
                  <p className="text-slate-500">
                    {t('plans.noPlans')}
                  </p>
                </div>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 lg:gap-8">
                {plans.map((plan) => (
                  <PlanCard
                    key={plan.id}
                    plan={plan}
                    isRecommended={plan.name === recommendedPlanName}
                    onSelect={handleSelectPlan}
                    ctaText={t('plans.getApiKey')}
                  />
                ))}
              </div>
            )}

            {/* Footer note */}
            <div className="text-center pt-4 pb-2 px-2">
              <p className="text-sm text-slate-500 max-w-xl mx-auto break-words">
                {t('plans.sandboxNote')}
              </p>
              <p className="text-sm text-slate-500 mt-2 break-words">
                {t('plans.inquiries')}{' '}
                <a
                  href="mailto:sales@example.com"
                  className="text-emerald-600 hover:text-emerald-700 font-medium"
                >
                  {t('plans.contactSales')}
                </a>
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
};
