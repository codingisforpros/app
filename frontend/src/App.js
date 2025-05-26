import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Chart as ChartJS, ArcElement, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Title } from 'chart.js';
import { Pie, Line } from 'react-chartjs-2';
import { LineChart, Line as RechartsLine, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Area, AreaChart, Bar, BarChart } from 'recharts';
import { PlusIcon, PencilIcon, TrashIcon, EyeIcon, UserIcon, ArrowRightOnRectangleIcon, ChartBarIcon, CurrencyDollarIcon, TrophyIcon, CogIcon, AdjustmentsHorizontalIcon, BeakerIcon, DocumentArrowDownIcon, ExclamationTriangleIcon, CheckCircleIcon } from '@heroicons/react/24/outline';
import './App.css';

ChartJS.register(ArcElement, Tooltip, Legend, CategoryScale, LinearScale, PointElement, LineElement, Title);

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const ASSET_TYPES = {
  stocks: 'Stocks',
  mutual_funds: 'Mutual Funds',
  cryptocurrency: 'Cryptocurrency',
  real_estate: 'Real Estate',
  fixed_deposits: 'Fixed Deposits',
  gold: 'Gold',
  others: 'Others'
};

const DEFAULT_GROWTH_RATES = {
  stocks: 12,
  mutual_funds: 10,
  cryptocurrency: 15,
  real_estate: 8,
  fixed_deposits: 6,
  gold: 8,
  others: 7
};

function App() {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [currentView, setCurrentView] = useState('dashboard');
  const [assets, setAssets] = useState([]);
  const [dashboard, setDashboard] = useState(null);
  const [goldPrices, setGoldPrices] = useState(null);
  const [milestones, setMilestones] = useState([]);
  const [projections, setProjections] = useState([]);
  
  // Advanced Analytics States
  const [monteCarloData, setMonteCarloData] = useState(null);
  const [financialHealthScore, setFinancialHealthScore] = useState(null);
  const [performanceAttribution, setPerformanceAttribution] = useState(null);
  const [taxOptimization, setTaxOptimization] = useState(null);
  
  const [showModal, setShowModal] = useState(false);
  const [showMilestoneModal, setShowMilestoneModal] = useState(false);
  const [showProjectionSettings, setShowProjectionSettings] = useState(false);
  const [showAnalyticsModal, setShowAnalyticsModal] = useState(false);
  const [editingAsset, setEditingAsset] = useState(null);
  const [loading, setLoading] = useState(false);
  
  // Auth form states
  const [authMode, setAuthMode] = useState('login');
  const [authForm, setAuthForm] = useState({
    name: '',
    email: '',
    password: ''
  });

  // Asset form states
  const [assetForm, setAssetForm] = useState({
    asset_type: 'stocks',
    name: '',
    purchase_value: '',
    current_value: '',
    purchase_date: new Date().toISOString().split('T')[0],
    metadata: {},
    // SIP fields
    monthly_sip_amount: '',
    sip_start_date: '',
    step_up_percentage: '',
    is_sip_active: false
  });

  // Milestone form states
  const [milestoneForm, setMilestoneForm] = useState({
    name: '',
    target_amount: '',
    target_date: ''
  });

  // Projection states
  const [projectionInputs, setProjectionInputs] = useState([]);
  const [customGrowthRates, setCustomGrowthRates] = useState(DEFAULT_GROWTH_RATES);
  const [projectionYears, setProjectionYears] = useState(20);

  useEffect(() => {
    if (token) {
      fetchUserData();
      setCurrentView('dashboard');
    }
  }, [token]);

  useEffect(() => {
    if (user) {
      if (currentView === 'dashboard') {
        fetchDashboard();
        fetchGoldPrices();
      } else if (currentView === 'assets') {
        fetchAssets();
      } else if (currentView === 'projections') {
        fetchMilestones();
        generateProjections();
      } else if (currentView === 'analytics') {
        fetchAdvancedAnalytics();
      }
    }
  }, [user, currentView]);

  const fetchUserData = async () => {
    try {
      const response = await axios.get(`${API}/me`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user data:', error);
      logout();
    }
  };

  const fetchDashboard = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/dashboard`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDashboard(response.data);
    } catch (error) {
      console.error('Failed to fetch dashboard:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchAssets = async () => {
    try {
      setLoading(true);
      const response = await axios.get(`${API}/assets`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setAssets(response.data);
    } catch (error) {
      console.error('Failed to fetch assets:', error);
    } finally {
      setLoading(false);
    }
  };

  const fetchGoldPrices = async () => {
    try {
      const response = await axios.get(`${API}/gold-prices`);
      setGoldPrices(response.data);
    } catch (error) {
      console.error('Failed to fetch gold prices:', error);
    }
  };

  const fetchMilestones = async () => {
    try {
      const response = await axios.get(`${API}/milestones`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setMilestones(response.data);
    } catch (error) {
      console.error('Failed to fetch milestones:', error);
    }
  };

  const fetchAdvancedAnalytics = async () => {
    try {
      setLoading(true);
      
      // Fetch all analytics in parallel
      const [healthResponse, performanceResponse, taxResponse, monteCarloResponse] = await Promise.all([
        axios.get(`${API}/analytics/financial-health-score`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/analytics/performance-attribution`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/analytics/tax-optimization`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${API}/analytics/monte-carlo?years=20&volatility=15&simulations=5000`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      setFinancialHealthScore(healthResponse.data);
      setPerformanceAttribution(performanceResponse.data);
      setTaxOptimization(taxResponse.data);
      setMonteCarloData(monteCarloResponse.data);
    } catch (error) {
      console.error('Failed to fetch advanced analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const generateProjections = async () => {
    if (!dashboard) return;

    try {
      const projectionData = Object.entries(dashboard.asset_allocation).map(([assetType, currentValue]) => {
        // Get SIP data for this asset type from assets
        const assetOfType = assets.find(asset => asset.asset_type === assetType && asset.is_sip_active);
        const totalMonthlySIP = assets
          .filter(asset => asset.asset_type === assetType && asset.is_sip_active)
          .reduce((sum, asset) => sum + (asset.monthly_sip_amount || 0), 0);
        const avgStepUp = assets
          .filter(asset => asset.asset_type === assetType && asset.is_sip_active)
          .reduce((sum, asset) => sum + (asset.step_up_percentage || 0), 0) / 
          Math.max(assets.filter(asset => asset.asset_type === assetType && asset.is_sip_active).length, 1);

        return {
          asset_class: assetType,
          current_value: currentValue,
          annual_growth_rate: customGrowthRates[assetType] || 7,
          annual_investment: currentValue * 0.05, // 5% additional investment per year
          years: projectionYears,
          monthly_sip_amount: totalMonthlySIP,
          step_up_percentage: avgStepUp || 0
        };
      });

      setProjectionInputs(projectionData);

      if (projectionData.length > 0) {
        const response = await axios.post(`${API}/projections/calculate`, projectionData, {
          headers: { Authorization: `Bearer ${token}` }
        });
        setProjections(response.data);
      }
    } catch (error) {
      console.error('Failed to generate projections:', error);
    }
  };

  const handleAuth = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const endpoint = authMode === 'login' ? 'login' : 'register';
      const response = await axios.post(`${API}/${endpoint}`, authForm);
      
      const newToken = response.data.access_token;
      setToken(newToken);
      localStorage.setItem('token', newToken);
      
      setAuthForm({ name: '', email: '', password: '' });
    } catch (error) {
      alert(error.response?.data?.detail || 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    setToken(null);
    setUser(null);
    localStorage.removeItem('token');
    setCurrentView('dashboard');
  };

  const handleAssetSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      const assetData = {
        ...assetForm,
        purchase_value: parseFloat(assetForm.purchase_value),
        current_value: parseFloat(assetForm.current_value),
        purchase_date: new Date(assetForm.purchase_date).toISOString(),
        monthly_sip_amount: parseFloat(assetForm.monthly_sip_amount) || 0,
        step_up_percentage: parseFloat(assetForm.step_up_percentage) || 0,
        sip_start_date: assetForm.sip_start_date ? new Date(assetForm.sip_start_date).toISOString() : null
      };

      // For gold assets, add weight and purity to metadata
      if (assetForm.asset_type === 'gold') {
        assetData.metadata = {
          ...assetForm.metadata,
          weight_grams: parseFloat(assetForm.metadata.weight_grams || 0),
          purity: assetForm.metadata.purity || '24k'
        };
      }

      if (editingAsset) {
        await axios.put(`${API}/assets/${editingAsset.id}`, {
          name: assetData.name,
          current_value: assetData.current_value,
          metadata: assetData.metadata,
          monthly_sip_amount: assetData.monthly_sip_amount,
          step_up_percentage: assetData.step_up_percentage,
          is_sip_active: assetData.is_sip_active
        }, {
          headers: { Authorization: `Bearer ${token}` }
        });
      } else {
        await axios.post(`${API}/assets`, assetData, {
          headers: { Authorization: `Bearer ${token}` }
        });
      }

      setShowModal(false);
      setEditingAsset(null);
      setAssetForm({
        asset_type: 'stocks',
        name: '',
        purchase_value: '',
        current_value: '',
        purchase_date: new Date().toISOString().split('T')[0],
        metadata: {},
        monthly_sip_amount: '',
        sip_start_date: '',
        step_up_percentage: '',
        is_sip_active: false
      });

      if (currentView === 'assets') {
        fetchAssets();
      } else {
        fetchDashboard();
      }
    } catch (error) {
      alert(error.response?.data?.detail || 'Failed to save asset');
    } finally {
      setLoading(false);
    }
  };

  const handleMilestoneSubmit = async (e) => {
    e.preventDefault();
    try {
      setLoading(true);
      await axios.post(`${API}/milestones`, {
        name: milestoneForm.name,
        target_amount: parseFloat(milestoneForm.target_amount),
        target_date: new Date(milestoneForm.target_date).toISOString()
      }, {
        headers: { Authorization: `Bearer ${token}` }
      });

      setShowMilestoneModal(false);
      setMilestoneForm({ name: '', target_amount: '', target_date: '' });
      fetchMilestones();
    } catch (error) {
      alert('Failed to save milestone');
    } finally {
      setLoading(false);
    }
  };

  const handleEditAsset = (asset) => {
    setEditingAsset(asset);
    setAssetForm({
      asset_type: asset.asset_type,
      name: asset.name,
      purchase_value: asset.purchase_value.toString(),
      current_value: asset.current_value.toString(),
      purchase_date: asset.purchase_date.split('T')[0],
      metadata: asset.metadata || {},
      monthly_sip_amount: asset.monthly_sip_amount?.toString() || '',
      sip_start_date: asset.sip_start_date ? asset.sip_start_date.split('T')[0] : '',
      step_up_percentage: asset.step_up_percentage?.toString() || '',
      is_sip_active: asset.is_sip_active || false
    });
    setShowModal(true);
  };

  const handleDeleteAsset = async (assetId) => {
    if (!window.confirm('Are you sure you want to delete this asset?')) return;
    
    try {
      await axios.delete(`${API}/assets/${assetId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (currentView === 'assets') {
        fetchAssets();
      } else {
        fetchDashboard();
      }
    } catch (error) {
      alert('Failed to delete asset');
    }
  };

  const handleDeleteMilestone = async (milestoneId) => {
    if (!window.confirm('Are you sure you want to delete this milestone?')) return;
    
    try {
      await axios.delete(`${API}/milestones/${milestoneId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      fetchMilestones();
    } catch (error) {
      alert('Failed to delete milestone');
    }
  };

  const updateProjectionSettings = () => {
    generateProjections();
    setShowProjectionSettings(false);
  };

  const getPieChartData = () => {
    if (!dashboard?.asset_allocation) return null;

    const labels = Object.keys(dashboard.asset_allocation).map(key => ASSET_TYPES[key] || key);
    const data = Object.values(dashboard.asset_allocation);
    
    const colors = [
      '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
      '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
    ];

    return {
      labels,
      datasets: [{
        data,
        backgroundColor: colors.slice(0, labels.length),
        borderWidth: 2
      }]
    };
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-IN', {
      style: 'currency',
      currency: 'INR'
    }).format(amount);
  };

  const calculateMilestoneProgress = (milestone) => {
    if (!dashboard) return 0;
    return Math.min((dashboard.total_net_worth / milestone.target_amount) * 100, 100);
  };

  const getProjectionChartData = () => {
    return projections.map(projection => ({
      ...projection,
      sip_vs_lumpsum: projection.sip_contribution + projection.lumpsum_contribution
    }));
  };

  const getHealthScoreColor = (score) => {
    if (score >= 800) return 'text-green-600';
    if (score >= 600) return 'text-blue-600';
    if (score >= 400) return 'text-yellow-600';
    return 'text-red-600';
  };

  const getHealthScoreLabel = (score) => {
    if (score >= 800) return 'Excellent';
    if (score >= 600) return 'Good';
    if (score >= 400) return 'Fair';
    return 'Poor';
  };

  const getMonteCarloChartData = () => {
    if (!monteCarloData) return null;
    
    return monteCarloData.years.map((year, index) => ({
      year,
      worst_case: monteCarloData.percentile_10[index],
      pessimistic: monteCarloData.percentile_25[index],
      most_likely: monteCarloData.percentile_50[index],
      optimistic: monteCarloData.percentile_75[index],
      best_case: monteCarloData.percentile_90[index]
    }));
  };

  if (!token) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-100 flex items-center justify-center p-4">
        <div className="bg-white rounded-xl shadow-xl p-8 w-full max-w-md">
          <div className="text-center mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">Wealth Tracker</h1>
            <p className="text-gray-600">Advanced Financial Analytics Platform</p>
          </div>

          <div className="flex mb-6">
            <button
              onClick={() => setAuthMode('login')}
              className={`flex-1 py-2 px-4 rounded-l-lg font-medium ${
                authMode === 'login' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-200 text-gray-700'
              }`}
            >
              Login
            </button>
            <button
              onClick={() => setAuthMode('register')}
              className={`flex-1 py-2 px-4 rounded-r-lg font-medium ${
                authMode === 'register' 
                  ? 'bg-blue-600 text-white' 
                  : 'bg-gray-200 text-gray-700'
              }`}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleAuth} className="space-y-4">
            {authMode === 'register' && (
              <input
                type="text"
                placeholder="Full Name"
                value={authForm.name}
                onChange={(e) => setAuthForm({...authForm, name: e.target.value})}
                className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                required
              />
            )}
            <input
              type="email"
              placeholder="Email"
              value={authForm.email}
              onChange={(e) => setAuthForm({...authForm, email: e.target.value})}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
            <input
              type="password"
              placeholder="Password"
              value={authForm.password}
              onChange={(e) => setAuthForm({...authForm, password: e.target.value})}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              required
            />
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-blue-600 text-white py-3 rounded-lg font-medium hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {loading ? 'Please wait...' : (authMode === 'login' ? 'Login' : 'Register')}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between items-center h-16">
            <div className="flex items-center">
              <h1 className="text-2xl font-bold text-gray-900">Wealth Tracker Pro</h1>
              <span className="ml-2 text-xs bg-gradient-to-r from-purple-500 to-pink-500 text-white px-2 py-1 rounded-full">ADVANCED</span>
            </div>
            
            <nav className="flex space-x-8">
              <button
                onClick={() => setCurrentView('dashboard')}
                className={`px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-2 ${
                  currentView === 'dashboard'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <ChartBarIcon className="h-4 w-4" />
                <span>Dashboard</span>
              </button>
              <button
                onClick={() => setCurrentView('assets')}
                className={`px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-2 ${
                  currentView === 'assets'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <CurrencyDollarIcon className="h-4 w-4" />
                <span>Assets</span>
              </button>
              <button
                onClick={() => setCurrentView('projections')}
                className={`px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-2 ${
                  currentView === 'projections'
                    ? 'bg-blue-100 text-blue-700'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <TrophyIcon className="h-4 w-4" />
                <span>Projections</span>
              </button>
              <button
                onClick={() => setCurrentView('analytics')}
                className={`px-3 py-2 rounded-md text-sm font-medium flex items-center space-x-2 ${
                  currentView === 'analytics'
                    ? 'bg-purple-100 text-purple-700'
                    : 'text-gray-600 hover:text-gray-900'
                }`}
              >
                <BeakerIcon className="h-4 w-4" />
                <span>Analytics</span>
              </button>
            </nav>

            <div className="flex items-center space-x-4">
              <div className="flex items-center space-x-2">
                <UserIcon className="h-5 w-5 text-gray-600" />
                <span className="text-sm text-gray-700">{user?.name}</span>
              </div>
              <button
                onClick={logout}
                className="p-2 text-gray-600 hover:text-gray-900"
              >
                <ArrowRightOnRectangleIcon className="h-5 w-5" />
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {currentView === 'dashboard' && dashboard && (
          <div className="space-y-6">
            {/* Quick Financial Health Score */}
            {financialHealthScore && (
              <div className={`bg-gradient-to-r from-purple-500 to-pink-500 p-6 rounded-lg shadow text-white`}>
                <div className="flex justify-between items-center">
                  <div>
                    <h3 className="text-lg font-semibold mb-2">Financial Health Score</h3>
                    <p className="text-3xl font-bold">{financialHealthScore.overall_score}/1000</p>
                    <p className="text-sm opacity-90">{getHealthScoreLabel(financialHealthScore.overall_score)} Financial Health</p>
                  </div>
                  <div className="text-right">
                    <button
                      onClick={() => setCurrentView('analytics')}
                      className="bg-white/20 hover:bg-white/30 px-4 py-2 rounded-lg transition-colors"
                    >
                      View Full Analytics
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Stats Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-sm font-medium text-gray-500">Total Net Worth</h3>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(dashboard.total_net_worth)}</p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-sm font-medium text-gray-500">Total Investment</h3>
                <p className="text-2xl font-bold text-gray-900">{formatCurrency(dashboard.total_investment)}</p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-sm font-medium text-gray-500">Gain/Loss</h3>
                <p className={`text-2xl font-bold ${dashboard.total_gain_loss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {formatCurrency(dashboard.total_gain_loss)}
                </p>
              </div>
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-sm font-medium text-gray-500">Gain/Loss %</h3>
                <p className={`text-2xl font-bold ${dashboard.gain_loss_percentage >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                  {dashboard.gain_loss_percentage.toFixed(2)}%
                </p>
              </div>
            </div>

            {/* Gold Prices Card */}
            {goldPrices && (
              <div className="bg-gradient-to-r from-yellow-400 to-orange-500 p-6 rounded-lg shadow text-white">
                <h3 className="text-lg font-semibold mb-4">Live Gold Prices (INR per gram)</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm opacity-90">22K Gold</p>
                    <p className="text-2xl font-bold">₹{goldPrices.gold_22k.toFixed(2)}</p>
                  </div>
                  <div>
                    <p className="text-sm opacity-90">24K Gold</p>
                    <p className="text-2xl font-bold">₹{goldPrices.gold_24k.toFixed(2)}</p>
                  </div>
                </div>
                <p className="text-xs opacity-75 mt-2">
                  Last updated: {new Date(goldPrices.timestamp).toLocaleString()}
                </p>
              </div>
            )}

            {/* Charts and Recent Assets */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Asset Allocation */}
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Asset Allocation</h3>
                {getPieChartData() ? (
                  <div className="h-64">
                    <Pie data={getPieChartData()} options={{ maintainAspectRatio: false }} />
                  </div>
                ) : (
                  <p className="text-gray-500 text-center py-8">No assets to display</p>
                )}
              </div>

              {/* Recent Assets */}
              <div className="bg-white p-6 rounded-lg shadow">
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-lg font-semibold text-gray-900">Recent Assets</h3>
                  <button
                    onClick={() => setShowModal(true)}
                    className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2"
                  >
                    <PlusIcon className="h-4 w-4" />
                    <span>Add Asset</span>
                  </button>
                </div>
                <div className="space-y-3">
                  {dashboard.recent_assets.map(asset => (
                    <div key={asset.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                      <div>
                        <p className="font-medium text-gray-900">{asset.name}</p>
                        <p className="text-sm text-gray-500">{ASSET_TYPES[asset.asset_type]}</p>
                        {asset.is_sip_active && (
                          <p className="text-xs text-blue-600">SIP: {formatCurrency(asset.monthly_sip_amount)}/month</p>
                        )}
                        {asset.metadata?.auto_calculated && (
                          <p className="text-xs text-green-600">Auto-updated</p>
                        )}
                      </div>
                      <div className="text-right">
                        <p className="font-medium">{formatCurrency(asset.current_value)}</p>
                        <div className="flex space-x-2">
                          <button
                            onClick={() => handleEditAsset(asset)}
                            className="text-blue-600 hover:text-blue-800"
                          >
                            <PencilIcon className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => handleDeleteAsset(asset.id)}
                            className="text-red-600 hover:text-red-800"
                          >
                            <TrashIcon className="h-4 w-4" />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {currentView === 'analytics' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-gray-900">Advanced Analytics</h2>
              <button
                onClick={fetchAdvancedAnalytics}
                className="bg-purple-600 text-white px-4 py-2 rounded-lg hover:bg-purple-700 flex items-center space-x-2"
              >
                <BeakerIcon className="h-4 w-4" />
                <span>Refresh Analytics</span>
              </button>
            </div>

            {loading ? (
              <div className="flex justify-center items-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-purple-600"></div>
              </div>
            ) : (
              <div className="space-y-6">
                {/* Financial Health Score */}
                {financialHealthScore && (
                  <div className="bg-white p-6 rounded-lg shadow">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Financial Health Score</h3>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <div>
                        <div className="flex items-center space-x-4 mb-4">
                          <div className="text-4xl font-bold text-purple-600">
                            {financialHealthScore.overall_score}
                          </div>
                          <div>
                            <div className="text-sm text-gray-500">out of 1000</div>
                            <div className={`text-lg font-medium ${getHealthScoreColor(financialHealthScore.overall_score)}`}>
                              {getHealthScoreLabel(financialHealthScore.overall_score)}
                            </div>
                          </div>
                        </div>
                        
                        <div className="space-y-3">
                          {Object.entries(financialHealthScore.category_scores).map(([category, score]) => (
                            <div key={category} className="flex justify-between items-center">
                              <span className="text-sm text-gray-600 capitalize">{category.replace('_', ' ')}</span>
                              <div className="flex items-center space-x-2">
                                <div className="w-24 bg-gray-200 rounded-full h-2">
                                  <div 
                                    className="bg-purple-600 h-2 rounded-full"
                                    style={{ width: `${(score / 200) * 100}%` }}
                                  ></div>
                                </div>
                                <span className="text-sm font-medium">{score}/200</span>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3">Recommendations</h4>
                        <div className="space-y-2">
                          {financialHealthScore.recommendations.map((rec, index) => (
                            <div key={index} className="flex items-start space-x-2">
                              <ExclamationTriangleIcon className="h-4 w-4 text-yellow-500 mt-0.5" />
                              <span className="text-sm text-gray-600">{rec}</span>
                            </div>
                          ))}
                        </div>
                        
                        <h4 className="font-medium text-gray-900 mb-3 mt-4">Strengths</h4>
                        <div className="space-y-2">
                          {financialHealthScore.strengths.map((strength, index) => (
                            <div key={index} className="flex items-start space-x-2">
                              <CheckCircleIcon className="h-4 w-4 text-green-500 mt-0.5" />
                              <span className="text-sm text-gray-600">{strength}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Monte Carlo Simulation */}
                {monteCarloData && (
                  <div className="bg-white p-6 rounded-lg shadow">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Monte Carlo Simulation (20 Years)</h3>
                    <div className="h-96 mb-4">
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={getMonteCarloChartData()}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis dataKey="year" />
                          <YAxis tickFormatter={(value) => `₹${(value / 100000).toFixed(1)}L`} />
                          <RechartsTooltip 
                            formatter={(value, name) => [formatCurrency(value), name]}
                            labelFormatter={(year) => `Year ${year}`}
                          />
                          <Area type="monotone" dataKey="best_case" stroke="#10B981" fill="#6EE7B7" fillOpacity={0.1} name="Best Case (90th percentile)" />
                          <Area type="monotone" dataKey="optimistic" stroke="#3B82F6" fill="#93C5FD" fillOpacity={0.2} name="Optimistic (75th percentile)" />
                          <Area type="monotone" dataKey="most_likely" stroke="#6366F1" fill="#A5B4FC" fillOpacity={0.4} name="Most Likely (50th percentile)" />
                          <Area type="monotone" dataKey="pessimistic" stroke="#F59E0B" fill="#FCD34D" fillOpacity={0.2} name="Pessimistic (25th percentile)" />
                          <Area type="monotone" dataKey="worst_case" stroke="#EF4444" fill="#FCA5A5" fillOpacity={0.1} name="Worst Case (10th percentile)" />
                        </AreaChart>
                      </ResponsiveContainer>
                    </div>
                    
                    <div className="grid grid-cols-5 gap-4">
                      {Object.entries(monteCarloData.final_values).map(([scenario, value]) => (
                        <div key={scenario} className="text-center">
                          <div className="text-xs text-gray-500 capitalize">{scenario.replace('_', ' ')}</div>
                          <div className="text-lg font-bold">{formatCurrency(value)}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Performance Attribution */}
                {performanceAttribution && (
                  <div className="bg-white p-6 rounded-lg shadow">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Performance Attribution</h3>
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3">Best Performers</h4>
                        <div className="space-y-2">
                          {performanceAttribution.best_performers.map((asset, index) => (
                            <div key={index} className="flex justify-between items-center p-2 bg-green-50 rounded">
                              <span className="text-sm text-gray-900">{asset.name}</span>
                              <span className="text-sm font-medium text-green-600">
                                +{asset.return_percentage.toFixed(1)}%
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                      
                      <div>
                        <h4 className="font-medium text-gray-900 mb-3">Sector Analysis</h4>
                        <div className="space-y-2">
                          {Object.entries(performanceAttribution.sector_analysis).map(([sector, data]) => (
                            <div key={sector} className="flex justify-between items-center">
                              <span className="text-sm text-gray-600">{sector}</span>
                              <div className="text-right">
                                <div className="text-sm font-medium">{data.allocation_percentage.toFixed(1)}%</div>
                                <div className={`text-xs ${data.average_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                                  {data.average_return.toFixed(1)}% return
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    </div>
                  </div>
                )}

                {/* Tax Optimization */}
                {taxOptimization && (
                  <div className="bg-white p-6 rounded-lg shadow">
                    <h3 className="text-lg font-semibold text-gray-900 mb-4">Tax Optimization</h3>
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                      <div className="bg-red-50 p-4 rounded-lg">
                        <h4 className="font-medium text-red-800 mb-2">Tax Liability</h4>
                        <div className="text-2xl font-bold text-red-600">
                          {formatCurrency(taxOptimization.total_tax_liability)}
                        </div>
                        <div className="text-sm text-red-600">
                          Effective Rate: {taxOptimization.effective_tax_rate.toFixed(2)}%
                        </div>
                      </div>
                      
                      <div className="bg-blue-50 p-4 rounded-lg">
                        <h4 className="font-medium text-blue-800 mb-2">LTCG Details</h4>
                        <div className="text-lg font-bold text-blue-600">
                          {formatCurrency(taxOptimization.ltcg_liability)}
                        </div>
                        <div className="text-sm text-blue-600">
                          Gains: {formatCurrency(taxOptimization.current_year_tax.ltcg_gains)}
                        </div>
                      </div>
                      
                      <div className="bg-orange-50 p-4 rounded-lg">
                        <h4 className="font-medium text-orange-800 mb-2">STCG Details</h4>
                        <div className="text-lg font-bold text-orange-600">
                          {formatCurrency(taxOptimization.stcg_liability)}
                        </div>
                        <div className="text-sm text-orange-600">
                          Gains: {formatCurrency(taxOptimization.current_year_tax.stcg_gains)}
                        </div>
                      </div>
                    </div>
                    
                    {taxOptimization.tax_saving_opportunities.length > 0 && (
                      <div className="mt-6">
                        <h4 className="font-medium text-gray-900 mb-3">Tax Saving Opportunities</h4>
                        <div className="space-y-2">
                          {taxOptimization.tax_saving_opportunities.map((opportunity, index) => (
                            <div key={index} className="p-3 bg-yellow-50 rounded border-l-4 border-yellow-400">
                              <div className="text-sm text-gray-800">{opportunity.description}</div>
                              {opportunity.potential_tax_saving && (
                                <div className="text-xs text-green-600 mt-1">
                                  Potential Saving: {formatCurrency(opportunity.potential_tax_saving)}
                                </div>
                              )}
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {/* Other views remain the same as before */}
        {currentView === 'assets' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-gray-900">My Assets</h2>
              <button
                onClick={() => setShowModal(true)}
                className="bg-blue-600 text-white px-4 py-2 rounded-lg hover:bg-blue-700 flex items-center space-x-2"
              >
                <PlusIcon className="h-4 w-4" />
                <span>Add Asset</span>
              </button>
            </div>

            <div className="bg-white rounded-lg shadow overflow-hidden">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Asset</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Type</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Purchase Value</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Current Value</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">SIP Details</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Gain/Loss</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Actions</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {assets.map(asset => {
                    const gainLoss = asset.current_value - asset.purchase_value;
                    const gainLossPercentage = (gainLoss / asset.purchase_value) * 100;
                    
                    return (
                      <tr key={asset.id}>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="text-sm font-medium text-gray-900">{asset.name}</div>
                          {asset.metadata?.auto_calculated && (
                            <div className="text-xs text-green-600">Auto-updated</div>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className="text-sm text-gray-500">{ASSET_TYPES[asset.asset_type]}</span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {formatCurrency(asset.purchase_value)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                          {formatCurrency(asset.current_value)}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          {asset.is_sip_active ? (
                            <div className="text-sm">
                              <div className="text-blue-600">{formatCurrency(asset.monthly_sip_amount)}/month</div>
                              {asset.step_up_percentage > 0 && (
                                <div className="text-xs text-gray-500">Step-up: {asset.step_up_percentage}%</div>
                              )}
                            </div>
                          ) : (
                            <span className="text-sm text-gray-400">No SIP</span>
                          )}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className={`text-sm ${gainLoss >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                            {formatCurrency(gainLoss)} ({gainLossPercentage.toFixed(2)}%)
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <div className="flex space-x-2">
                            <button
                              onClick={() => handleEditAsset(asset)}
                              className="text-blue-600 hover:text-blue-900"
                            >
                              <PencilIcon className="h-4 w-4" />
                            </button>
                            <button
                              onClick={() => handleDeleteAsset(asset.id)}
                              className="text-red-600 hover:text-red-900"
                            >
                              <TrashIcon className="h-4 w-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {currentView === 'projections' && (
          <div className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold text-gray-900">Net Worth Projections</h2>
              <div className="flex space-x-3">
                <button
                  onClick={() => setShowProjectionSettings(true)}
                  className="bg-gray-600 text-white px-4 py-2 rounded-lg hover:bg-gray-700 flex items-center space-x-2"
                >
                  <AdjustmentsHorizontalIcon className="h-4 w-4" />
                  <span>Settings</span>
                </button>
                <button
                  onClick={() => setShowMilestoneModal(true)}
                  className="bg-green-600 text-white px-4 py-2 rounded-lg hover:bg-green-700 flex items-center space-x-2"
                >
                  <TrophyIcon className="h-4 w-4" />
                  <span>Add Milestone</span>
                </button>
              </div>
            </div>

            {/* Milestones */}
            {milestones.length > 0 && (
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">Financial Milestones</h3>
                <div className="space-y-4">
                  {milestones.map(milestone => {
                    const progress = calculateMilestoneProgress(milestone);
                    const isCompleted = progress >= 100;
                    
                    return (
                      <div key={milestone.id} className="border rounded-lg p-4">
                        <div className="flex justify-between items-center mb-2">
                          <h4 className="font-medium text-gray-900">{milestone.name}</h4>
                          <div className="flex items-center space-x-2">
                            <span className="text-sm text-gray-500">{formatCurrency(milestone.target_amount)}</span>
                            <button
                              onClick={() => handleDeleteMilestone(milestone.id)}
                              className="text-red-600 hover:text-red-800"
                            >
                              <TrashIcon className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                        <div className="mb-2">
                          <div className="flex justify-between items-center text-sm">
                            <span className={isCompleted ? 'text-green-600' : 'text-gray-600'}>
                              Progress: {progress.toFixed(1)}%
                            </span>
                            <span className="text-gray-500">
                              Target: {new Date(milestone.target_date).toLocaleDateString()}
                            </span>
                          </div>
                          <div className="w-full bg-gray-200 rounded-full h-2 mt-1">
                            <div 
                              className={`h-2 rounded-full ${isCompleted ? 'bg-green-600' : 'bg-blue-600'}`}
                              style={{ width: `${Math.min(progress, 100)}%` }}
                            ></div>
                          </div>
                        </div>
                        {isCompleted && (
                          <p className="text-sm text-green-600 font-medium">🎉 Milestone Achieved!</p>
                        )}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Projection Chart */}
            {projections.length > 0 && (
              <div className="bg-white p-6 rounded-lg shadow">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">{projectionYears}-Year Net Worth Projection with SIP</h3>
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={getProjectionChartData()}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="year" />
                      <YAxis tickFormatter={(value) => `₹${(value / 100000).toFixed(1)}L`} />
                      <RechartsTooltip 
                        formatter={(value, name) => [formatCurrency(value), name]}
                        labelFormatter={(year) => `Year ${year}`}
                      />
                      <Area 
                        type="monotone" 
                        dataKey="total_value" 
                        stroke="#3B82F6" 
                        fill="#93C5FD" 
                        fillOpacity={0.6}
                        name="Total Net Worth"
                      />
                      <Area 
                        type="monotone" 
                        dataKey="sip_contribution" 
                        stroke="#10B981" 
                        fill="#6EE7B7" 
                        fillOpacity={0.4}
                        name="SIP Contribution"
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
                
                {/* Projection Summary */}
                <div className="mt-4 grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h4 className="text-sm font-medium text-blue-800">Current Net Worth</h4>
                    <p className="text-xl font-bold text-blue-900">
                      {dashboard ? formatCurrency(dashboard.total_net_worth) : '₹0'}
                    </p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <h4 className="text-sm font-medium text-green-800">10-Year Projection</h4>
                    <p className="text-xl font-bold text-green-900">
                      {projections[9] ? formatCurrency(projections[9].total_value) : '₹0'}
                    </p>
                  </div>
                  <div className="bg-purple-50 p-4 rounded-lg">
                    <h4 className="text-sm font-medium text-purple-800">{projectionYears}-Year Projection</h4>
                    <p className="text-xl font-bold text-purple-900">
                      {projections[projectionYears-1] ? formatCurrency(projections[projectionYears-1].total_value) : '₹0'}
                    </p>
                  </div>
                  <div className="bg-orange-50 p-4 rounded-lg">
                    <h4 className="text-sm font-medium text-orange-800">Total SIP ({projectionYears} years)</h4>
                    <p className="text-xl font-bold text-orange-900">
                      {projections[projectionYears-1] ? formatCurrency(projections[projectionYears-1].sip_contribution * projectionYears) : '₹0'}
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Modals remain the same as before */}
      {/* Add/Edit Asset Modal */}
      {showModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" style={{pointerEvents: 'none'}}>
          <div className="relative top-10 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white" style={{pointerEvents: 'auto'}}>
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">
                {editingAsset ? 'Edit Asset' : 'Add New Asset'}
              </h3>
              
              <form onSubmit={handleAssetSubmit} className="space-y-4 max-h-96 overflow-y-auto">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Asset Type</label>
                  <select
                    value={assetForm.asset_type}
                    onChange={(e) => setAssetForm({...assetForm, asset_type: e.target.value})}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    disabled={editingAsset}
                  >
                    {Object.entries(ASSET_TYPES).map(([key, value]) => (
                      <option key={key} value={key}>{value}</option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Asset Name</label>
                  <input
                    type="text"
                    value={assetForm.name}
                    onChange={(e) => setAssetForm({...assetForm, name: e.target.value})}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                {/* Gold specific fields */}
                {assetForm.asset_type === 'gold' && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Weight (grams)</label>
                      <input
                        type="number"
                        step="0.01"
                        value={assetForm.metadata.weight_grams || ''}
                        onChange={(e) => setAssetForm({
                          ...assetForm, 
                          metadata: {...assetForm.metadata, weight_grams: e.target.value}
                        })}
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                        required
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Purity</label>
                      <select
                        value={assetForm.metadata.purity || '24k'}
                        onChange={(e) => setAssetForm({
                          ...assetForm, 
                          metadata: {...assetForm.metadata, purity: e.target.value}
                        })}
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                      >
                        <option value="22k">22K Gold</option>
                        <option value="24k">24K Gold</option>
                      </select>
                    </div>
                  </>
                )}

                {!editingAsset && (
                  <>
                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Purchase Value</label>
                      <input
                        type="number"
                        step="0.01"
                        value={assetForm.purchase_value}
                        onChange={(e) => setAssetForm({...assetForm, purchase_value: e.target.value})}
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                        required
                      />
                    </div>

                    <div>
                      <label className="block text-sm font-medium text-gray-700 mb-1">Purchase Date</label>
                      <input
                        type="date"
                        value={assetForm.purchase_date}
                        onChange={(e) => setAssetForm({...assetForm, purchase_date: e.target.value})}
                        className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                        required
                      />
                    </div>
                  </>
                )}

                {(assetForm.asset_type !== 'gold' || editingAsset) && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Current Value</label>
                    <input
                      type="number"
                      step="0.01"
                      value={assetForm.current_value}
                      onChange={(e) => setAssetForm({...assetForm, current_value: e.target.value})}
                      className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                      required={assetForm.asset_type !== 'gold'}
                    />
                  </div>
                )}

                {/* SIP Configuration */}
                <div className="border-t pt-4">
                  <div className="flex items-center space-x-2 mb-3">
                    <input
                      type="checkbox"
                      id="is_sip_active"
                      checked={assetForm.is_sip_active}
                      onChange={(e) => setAssetForm({...assetForm, is_sip_active: e.target.checked})}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <label htmlFor="is_sip_active" className="text-sm font-medium text-gray-700">
                      Enable SIP (Systematic Investment Plan)
                    </label>
                  </div>

                  {assetForm.is_sip_active && (
                    <>
                      <div className="grid grid-cols-2 gap-3">
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Monthly SIP Amount</label>
                          <input
                            type="number"
                            step="0.01"
                            value={assetForm.monthly_sip_amount}
                            onChange={(e) => setAssetForm({...assetForm, monthly_sip_amount: e.target.value})}
                            className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                            placeholder="5000"
                          />
                        </div>
                        <div>
                          <label className="block text-sm font-medium text-gray-700 mb-1">Step-up % (Annual)</label>
                          <input
                            type="number"
                            step="0.1"
                            value={assetForm.step_up_percentage}
                            onChange={(e) => setAssetForm({...assetForm, step_up_percentage: e.target.value})}
                            className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                            placeholder="10"
                          />
                        </div>
                      </div>
                      <div className="mt-3">
                        <label className="block text-sm font-medium text-gray-700 mb-1">SIP Start Date</label>
                        <input
                          type="date"
                          value={assetForm.sip_start_date}
                          onChange={(e) => setAssetForm({...assetForm, sip_start_date: e.target.value})}
                          className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                        />
                      </div>
                    </>
                  )}
                </div>

                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowModal(false);
                      setEditingAsset(null);
                      setAssetForm({
                        asset_type: 'stocks',
                        name: '',
                        purchase_value: '',
                        current_value: '',
                        purchase_date: new Date().toISOString().split('T')[0],
                        metadata: {},
                        monthly_sip_amount: '',
                        sip_start_date: '',
                        step_up_percentage: '',
                        is_sip_active: false
                      });
                    }}
                    className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                  >
                    {loading ? 'Saving...' : (editingAsset ? 'Update' : 'Add Asset')}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Add Milestone Modal */}
      {showMilestoneModal && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" style={{pointerEvents: 'none'}}>
          <div className="relative top-20 mx-auto p-5 border w-96 shadow-lg rounded-md bg-white" style={{pointerEvents: 'auto'}}>
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Add Financial Milestone</h3>
              
              <form onSubmit={handleMilestoneSubmit} className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Milestone Name</label>
                  <input
                    type="text"
                    value={milestoneForm.name}
                    onChange={(e) => setMilestoneForm({...milestoneForm, name: e.target.value})}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., Buy House, Retirement, ₹1 Crore"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Target Amount</label>
                  <input
                    type="number"
                    step="0.01"
                    value={milestoneForm.target_amount}
                    onChange={(e) => setMilestoneForm({...milestoneForm, target_amount: e.target.value})}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    placeholder="e.g., 10000000"
                    required
                  />
                </div>

                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Target Date</label>
                  <input
                    type="date"
                    value={milestoneForm.target_date}
                    onChange={(e) => setMilestoneForm({...milestoneForm, target_date: e.target.value})}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                    required
                  />
                </div>

                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => {
                      setShowMilestoneModal(false);
                      setMilestoneForm({ name: '', target_amount: '', target_date: '' });
                    }}
                    className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                  >
                    Cancel
                  </button>
                  <button
                    type="submit"
                    disabled={loading}
                    className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50"
                  >
                    {loading ? 'Saving...' : 'Add Milestone'}
                  </button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Projection Settings Modal */}
      {showProjectionSettings && (
        <div className="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50" style={{pointerEvents: 'none'}}>
          <div className="relative top-10 mx-auto p-5 border w-full max-w-lg shadow-lg rounded-md bg-white" style={{pointerEvents: 'auto'}}>
            <div className="mt-3">
              <h3 className="text-lg font-medium text-gray-900 mb-4">Projection Settings</h3>
              
              <div className="space-y-4 max-h-96 overflow-y-auto">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">Projection Years</label>
                  <input
                    type="number"
                    min="5"
                    max="50"
                    value={projectionYears}
                    onChange={(e) => setProjectionYears(parseInt(e.target.value))}
                    className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
                  />
                </div>

                <div>
                  <h4 className="text-md font-medium text-gray-900 mb-3">Expected Annual Returns (%)</h4>
                  <div className="space-y-3">
                    {Object.entries(ASSET_TYPES).map(([key, value]) => (
                      <div key={key} className="flex justify-between items-center">
                        <label className="text-sm text-gray-700">{value}</label>
                        <input
                          type="number"
                          step="0.1"
                          min="0"
                          max="50"
                          value={customGrowthRates[key]}
                          onChange={(e) => setCustomGrowthRates({
                            ...customGrowthRates,
                            [key]: parseFloat(e.target.value)
                          })}
                          className="w-20 p-1 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 text-center"
                        />
                      </div>
                    ))}
                  </div>
                </div>

                <div className="flex justify-end space-x-3 pt-4">
                  <button
                    type="button"
                    onClick={() => setShowProjectionSettings(false)}
                    className="px-4 py-2 bg-gray-300 text-gray-700 rounded-md hover:bg-gray-400"
                  >
                    Cancel
                  </button>
                  <button
                    type="button"
                    onClick={updateProjectionSettings}
                    className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                  >
                    Update Projections
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;