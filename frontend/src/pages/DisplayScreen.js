import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Star } from 'lucide-react';
import { format } from 'date-fns';
import Header from '../components/Header';

const DisplayScreen = () => {
  const [feedback, setFeedback] = useState([]);

  useEffect(() => {
    const loadVisibleFeed = () => {
      if (document.visibilityState === 'visible') {
        fetchLiveFeed();
      }
    };

    loadVisibleFeed();
    const interval = setInterval(loadVisibleFeed, 30000);
    document.addEventListener('visibilitychange', loadVisibleFeed);

    return () => {
      clearInterval(interval);
      document.removeEventListener('visibilitychange', loadVisibleFeed);
    };
  }, []);

  const fetchLiveFeed = async () => {
    try {
      const response = await api.get('/display/live-feed', { cacheTtlMs: 5000 });
      setFeedback(response.data);
    } catch (error) {
      console.error('Failed to fetch live feed:', error);
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      Pending: 'bg-[#FFF4E5] text-[#DD6B20] border-[#DD6B20]',
      'In Progress': 'bg-[#E6F4FF] text-[#2B6CB0] border-[#2B6CB0]',
      Resolved: 'bg-[#E6F4EA] text-[#1E7E34] border-[#1E7E34]',
      Rejected: 'bg-[#FDE8E8] text-[#C53030] border-[#C53030]',
    };
    return colors[status] || '';
  };

  const renderStars = (rating) => {
    return (
      <div className="flex gap-1">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            size={24}
            className={star <= rating ? 'fill-[#F4C430] text-[#F4C430]' : 'text-gray-300'}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="min-h-screen flex flex-col bg-gradient-to-br from-[#721C24] via-[#4A1016] to-[#2D0A0E]">
      <Header logo="/ts-logo.png" />
      
      <div className="flex-1 p-8">
        {/* Header */}
        <div className="text-center mb-12">
          <div
            className="inline-block p-6 rounded-2xl mb-4"
            style={{
              backgroundImage: 'url(https://images.unsplash.com/photo-1764775086606-9b23aa61352a)',
              backgroundSize: 'cover',
              backgroundPosition: 'center',
            }}
          >
            <div className="bg-black/50 backdrop-blur-sm p-6 rounded-xl">
              <h1 className="text-6xl font-bold text-[#F4C430] mb-2">Temple Feedback</h1>
              <p className="text-2xl text-white/90">Live Status Board</p>
            </div>
          </div>
        </div>

      {/* Bento Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-7xl mx-auto">
        {feedback.map((item, index) => (
          <div
            key={item.id}
            data-testid={`display-feedback-${item.id}`}
            className="bg-white/95 backdrop-blur-sm rounded-2xl p-6 shadow-2xl border-t-4 border-[#F4C430] hover:scale-105 transition-transform duration-300"
            style={{ animationDelay: `${index * 0.1}s` }}
          >
            {/* Header */}
            <div className="flex items-start justify-between mb-4">
              <div>
                <h3 className="text-2xl font-bold text-[#721C24]">{item.complaint_id}</h3>
                <p className="text-lg text-[#4A5568] font-medium">{item.temple_name}</p>
              </div>
              <span
                className={`px-4 py-2 rounded-full text-sm font-bold border-2 ${
                  getStatusColor(item.status)
                }`}
              >
                {item.status}
              </span>
            </div>

            {/* Service */}
            <div className="mb-4">
              <p className="text-sm uppercase tracking-wider text-slate-500 mb-1">Service</p>
              <p className="text-xl font-semibold text-[#1A202C]">{item.service}</p>
            </div>

            {/* Rating */}
            <div className="mb-4">
              <p className="text-sm uppercase tracking-wider text-slate-500 mb-2">Rating</p>
              {renderStars(item.rating)}
            </div>

            {/* User Info */}
            <div className="mb-4">
              <p className="text-sm uppercase tracking-wider text-slate-500 mb-1">Devotee</p>
              <p className="text-lg font-medium text-[#1A202C]">{item.user_name}</p>
            </div>

            {/* Date */}
            <div className="pt-4 border-t border-[#E2E8F0]">
              <p className="text-sm text-[#4A5568]">
                {format(new Date(item.created_at), 'MMM dd, yyyy HH:mm')}
              </p>
            </div>

            {/* Video Indicator */}
            {(item.video_url || item.video_path) && (
              <div className="mt-3 flex items-center gap-2 text-[#721C24]">
                <div className="w-2 h-2 bg-[#721C24] rounded-full animate-pulse"></div>
                <span className="text-sm font-medium">Video Available</span>
              </div>
            )}
          </div>
        ))}
      </div>

      {/* Auto-refresh indicator */}
      <div className="fixed bottom-8 right-8 bg-white/90 backdrop-blur-sm px-6 py-3 rounded-full shadow-lg">
        <div className="flex items-center gap-2 text-[#721C24]">
          <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
          <span className="font-medium">Live Updates</span>
        </div>
      </div>
    </div>
    </div>
  );
};

export default DisplayScreen;