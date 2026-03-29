import { useState, useEffect } from 'react';
import api from '../utils/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell } from 'recharts';
import { Building2, Users, MessageSquare, CheckCircle, Clock, XCircle } from 'lucide-react';

// Temple colors - different color for each temple
const TEMPLE_COLORS = [
  '#721C24', // Maroon
  '#FF6B35', // Orange
  '#2B6CB0', // Blue
  '#38A169', // Green
  '#9F7AEA', // Purple
  '#DD6B20', // Burnt Orange
  '#319795', // Teal
  '#D53F8C', // Pink
  '#3182CE', // Light Blue
  '#805AD5', // Violet
];

const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchStats();
  }, []);

  const fetchStats = async () => {
    try {
      let response;
      try {
        response = await api.get('/dashboard/stats');
      } catch (innerError) {
        if (innerError.response?.status === 404) {
          response = await api.get('/stats');
        } else {
          throw innerError;
        }
      }
      setStats(response.data);
      setError(null);
    } catch (error) {
      console.error('Failed to fetch stats:', error);
      setError(error.response?.data?.detail || error.message || 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#721C24] text-xl">Loading...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-[#C53030] text-xl">Error loading dashboard: {error}</div>
      </div>
    );
  }

  const statCards = [
    {
      title: 'Total Temples',
      value: stats?.total_temples || 0,
      icon: Building2,
      color: 'border-t-[#721C24]',
      bgColor: 'bg-[#721C24]/5',
    },
    {
      title: 'Total Officers',
      value: stats?.total_officers || 0,
      icon: Users,
      color: 'border-t-[#F4C430]',
      bgColor: 'bg-[#F4C430]/10',
    },
    {
      title: 'Total Feedback',
      value: stats?.total_feedback || 0,
      icon: MessageSquare,
      color: 'border-t-[#FF9933]',
      bgColor: 'bg-[#FF9933]/10',
    },
    {
      title: 'Pending',
      value: stats?.pending || 0,
      icon: Clock,
      color: 'border-t-[#DD6B20]',
      bgColor: 'bg-[#DD6B20]/10',
    },
    {
      title: 'In Progress',
      value: stats?.in_progress || 0,
      icon: Clock,
      color: 'border-t-[#2B6CB0]',
      bgColor: 'bg-[#2B6CB0]/10',
    },
    {
      title: 'Resolved',
      value: stats?.resolved || 0,
      icon: CheckCircle,
      color: 'border-t-[#1E7E34]',
      bgColor: 'bg-[#1E7E34]/10',
    },
    {
      title: 'Rejected',
      value: stats?.rejected || 0,
      icon: XCircle,
      color: 'border-t-[#C53030]',
      bgColor: 'bg-[#C53030]/10',
    },
  ];

  const chartData = stats?.temple_stats?.map((t) => ({
    name: t._id,
    feedback: t.count,
  })) || [];

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-2">Dashboard</h1>
        <p className="text-[#4A5568]">Overview of all temple feedback and statistics</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div
              key={index}
              data-testid={`stat-${stat.title.toLowerCase().replace(' ', '-')}`}
              className={`bg-white rounded-2xl p-6 shadow-sm border-t-2 ${stat.color} hover:-translate-y-1 hover:shadow-md transition-all duration-300`}
            >
              <div className="flex items-center justify-between mb-4">
                <div className={`p-3 rounded-lg ${stat.bgColor}`}>
                  <Icon className="text-[#721C24]" size={24} strokeWidth={1.5} />
                </div>
              </div>
              <div>
                <p className="text-sm uppercase tracking-widest text-slate-500 mb-1">
                  {stat.title}
                </p>
                <p className="text-3xl font-bold text-[#721C24]">{stat.value}</p>
              </div>
            </div>
          );
        })}
      </div>

      {/* Temple-wise Feedback Chart */}
      {chartData.length > 0 && (
        <div className="bg-white rounded-2xl p-8 shadow-lg border-t-4 border-[#721C24]">
          <h2 className="text-3xl sm:text-4xl font-bold mb-6 text-[#721C24]">Temple-wise Feedback</h2>
          <div className="bg-[#FDFBF7] p-6 rounded-xl">
            <ResponsiveContainer width="100%" height={400}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E2E8F0" />
                <XAxis
                  dataKey="name"
                  tick={{ fill: '#721C24', fontSize: 14, fontWeight: 600 }}
                  angle={-25}
                  textAnchor="end"
                  height={120}
                />
                <YAxis tick={{ fill: '#721C24', fontSize: 14 }} />
                <Tooltip
                  contentStyle={{
                    backgroundColor: 'white',
                    border: '2px solid #721C24',
                    borderRadius: '12px',
                    boxShadow: '0 4px 6px rgba(0,0,0,0.1)',
                    padding: '12px'
                  }}
                  labelStyle={{ color: '#721C24', fontWeight: 'bold' }}
                  itemStyle={{ color: '#F4C430' }}
                />
                <Legend 
                  wrapperStyle={{ 
                    paddingTop: '20px',
                    fontSize: '14px',
                    fontWeight: 600
                  }}
                />
                <Bar 
                  dataKey="feedback" 
                  radius={[12, 12, 0, 0]}
                  label={{ 
                    position: 'top', 
                    fill: '#721C24',
                    fontSize: 16,
                    fontWeight: 'bold'
                  }}
                >
                  {chartData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={TEMPLE_COLORS[index % TEMPLE_COLORS.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
};

export default AdminDashboard;