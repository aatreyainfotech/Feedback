import { useState, useEffect } from 'react';
import api, { API } from '../utils/api';
import { Button } from '../components/ui/button';
import { Textarea } from '../components/ui/textarea';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { MessageSquare, CheckCircle, Clock, Play, Star } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

const OfficerDashboard = () => {
  const [feedback, setFeedback] = useState([]);
  const [stats, setStats] = useState(null);
  const [selectedFeedback, setSelectedFeedback] = useState(null);
  const [statusUpdate, setStatusUpdate] = useState('');
  const [officerNotes, setOfficerNotes] = useState('');
  const [videoPlaying, setVideoPlaying] = useState(false);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const rowsPerPage = 5;

  const videoPath = (selectedFeedback?.video_url || selectedFeedback?.video_path || '').replace(/^\/+/, '');
  const encodedVideoPath = videoPath ? videoPath.split('/').map(encodeURIComponent).join('/') : '';
  const videoSrc = encodedVideoPath ? `${API}/files/${encodedVideoPath}` : null;

  useEffect(() => {
    setVideoPlaying(false);
  }, [selectedFeedback]);

  useEffect(() => {
    let active = true;

    const loadDashboardData = async () => {
      setLoading(true);
      try {
        const [feedbackResponse, statsResponse] = await Promise.all([
          api.get('/feedback/officer', { cacheTtlMs: 5000 }),
          api.get('/dashboard/officer-stats', { cacheTtlMs: 5000 }),
        ]);

        if (!active) {
          return;
        }

        setFeedback(feedbackResponse.data);
        setStats(statsResponse.data);
      } catch (error) {
        toast.error('Failed to load dashboard data');
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    loadDashboardData();
    return () => {
      active = false;
    };
  }, []);

  const fetchFeedback = async () => {
    try {
      const response = await api.get('/feedback/officer', { forceRefresh: true });
      setFeedback(response.data);
    } catch (error) {
      toast.error('Failed to fetch feedback');
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get('/dashboard/officer-stats', { forceRefresh: true });
      setStats(response.data);
    } catch (error) {
      console.error('Failed to fetch stats');
    }
  };

  const handleStatusUpdate = async () => {
    if (!statusUpdate) {
      toast.error('Please select a status');
      return;
    }

    try {
      await api.put(`/feedback/${selectedFeedback.id}/status`, {
        status: statusUpdate,
        officer_notes: officerNotes || undefined,
      });
      toast.success('Status updated successfully');
      setSelectedFeedback(null);
      setStatusUpdate('');
      setOfficerNotes('');
      await Promise.all([fetchFeedback(), fetchStats()]);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update status');
    }
  };

  const openFeedbackDetail = (item) => {
    setSelectedFeedback(item);
    setStatusUpdate(item.status);
    setOfficerNotes(item.officer_notes || '');
  };

  const getStatusBadge = (status) => {
    const styles = {
      Pending: 'bg-[#FFF4E5] text-[#DD6B20] border border-[#DD6B20]/20',
      'In Progress': 'bg-[#E6F4FF] text-[#2B6CB0] border border-[#2B6CB0]/20',
      Resolved: 'bg-[#E6F4EA] text-[#1E7E34] border border-[#1E7E34]/20',
      Rejected: 'bg-[#FDE8E8] text-[#C53030] border border-[#C53030]/20',
    };
    return (
      <span className={`px-3 py-1 rounded-full text-xs font-medium ${styles[status] || ''}`}>
        {status}
      </span>
    );
  };

  const renderStars = (rating) => {
    return (
      <div className="flex gap-0.5">
        {[1, 2, 3, 4, 5].map((star) => (
          <Star
            key={star}
            size={16}
            className={star <= rating ? 'fill-[#F4C430] text-[#F4C430]' : 'text-gray-300'}
          />
        ))}
      </div>
    );
  };

  if (loading) {
    return <div className="text-center py-8">Loading...</div>;
  }

  const totalPages = Math.max(1, Math.ceil(feedback.length / rowsPerPage));
  const safePage = Math.min(currentPage, totalPages);
  const pagedFeedback = feedback.slice((safePage - 1) * rowsPerPage, safePage * rowsPerPage);
  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > totalPages) return;
    setCurrentPage(newPage);
  };

  const statCards = [
    {
      title: 'Total Feedback',
      value: stats?.total_assigned || stats?.total_feedback || 0,
      icon: MessageSquare,
      color: 'border-t-[#721C24]',
    },
    {
      title: 'Pending',
      value: stats?.pending || 0,
      icon: Clock,
      color: 'border-t-[#DD6B20]',
    },
    {
      title: 'In Progress',
      value: stats?.in_progress || 0,
      icon: Clock,
      color: 'border-t-[#2B6CB0]',
    },
    {
      title: 'Resolved',
      value: stats?.resolved || 0,
      icon: CheckCircle,
      color: 'border-t-[#1E7E34]',
    },
  ];

  return (
    <div className="space-y-6 feedback-page">
      <div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-2 text-[#721C24]">My Dashboard</h1>
        <p className="text-[#4A5568]">Manage feedback for your temple</p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {statCards.map((stat, index) => {
          const Icon = stat.icon;
          return (
            <div
              key={index}
              data-testid={`officer-stat-${stat.title.toLowerCase().replace(' ', '-')}`}
              className={`bg-white/90 backdrop-blur-sm rounded-2xl p-6 shadow-lg border-t-4 ${stat.color} hover:shadow-xl transition-all duration-300`}
            >
              <div className="flex items-center gap-3 mb-2">
                <Icon className="text-[#721C24]" size={24} strokeWidth={1.5} />
              </div>
              <p className="text-sm uppercase tracking-widest text-slate-500 mb-1">
                {stat.title}
              </p>
              <p className="text-3xl font-bold text-[#721C24]">{stat.value}</p>
            </div>
          );
        })}
      </div>

      {/* Feedback Table */}
      <div className="bg-white/90 backdrop-blur-sm rounded-2xl shadow-lg overflow-hidden">
        <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#FDFBF7] hover:bg-[#FDFBF7]">
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                ID
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Devotee Name
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Service
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Rating
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Status
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Date
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Assigned To
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider text-center">
                Video
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider text-center">
                Action
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pagedFeedback.map((item) => (
              <TableRow
                key={item.id}
                data-testid={`officer-feedback-row-${item.id}`}
                className="hover:bg-[#FFF9E6] transition-colors"
              >
                <TableCell className="font-medium">{item.complaint_id}</TableCell>
                <TableCell>
                  <div>
                    <div className="font-medium">{item.user_name}</div>
                    <div className="text-xs text-[#4A5568]">{item.user_mobile}</div>
                  </div>
                </TableCell>
                <TableCell className="text-[#4A5568]">{item.service}</TableCell>
                <TableCell>{renderStars(item.rating)}</TableCell>
                <TableCell>{getStatusBadge(item.status)}</TableCell>
                <TableCell className="text-[#4A5568]">
                  {format(new Date(item.created_at), 'MMM dd, yyyy')}
                </TableCell>
                <TableCell>
                  {item.assigned_officer_name ? (
                    <span className="text-sm font-medium text-[#1E7E34]">
                      {item.assigned_officer_name}
                    </span>
                  ) : (
                    <span className="text-sm text-[#4A5568]">Not assigned</span>
                  )}
                </TableCell>
                <TableCell className="text-center">
                  {(item.video_url || item.video_path) ? (
                    <button
                      onClick={() => openFeedbackDetail(item)}
                      data-testid={`officer-play-video-${item.id}`}
                      className="inline-flex items-center justify-center w-10 h-10 rounded-full bg-[#721C24] text-white hover:bg-[#5A161C] transition-all hover:scale-110"
                      title="Play Video"
                    >
                      <Play size={18} fill="white" />
                    </button>
                  ) : (
                    <span className="text-sm text-gray-400">No video</span>
                  )}
                </TableCell>
                <TableCell className="text-center">
                  <Button
                    size="sm"
                    onClick={() => openFeedbackDetail(item)}
                    data-testid={`view-feedback-${item.id}`}
                    className="bg-[#721C24] hover:bg-[#5A161C] text-white"
                  >
                    View & Update
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        </div>
        <div className="flex items-center justify-between p-4 bg-white border-t border-slate-200">
          <div className="text-sm text-slate-500">
            Showing {feedback.length === 0 ? 0 : (safePage - 1) * rowsPerPage + 1} - {Math.min(safePage * rowsPerPage, feedback.length)} of {feedback.length}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(safePage - 1)}
              disabled={safePage === 1}
              className="px-3 py-1 rounded-lg border border-slate-300 bg-white text-slate-600 hover:bg-slate-100 disabled:opacity-50"
            >
              Prev
            </button>
            {[...Array(totalPages)].map((_, idx) => {
              const page = idx + 1;
              return (
                <button
                  key={page}
                  onClick={() => handlePageChange(page)}
                  className={`px-3 py-1 rounded-lg border ${page === safePage ? 'border-[#721C24] bg-[#721C24] text-white' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100'}`}
                >
                  {page}
                </button>
              );
            })}
            <button
              onClick={() => handlePageChange(safePage + 1)}
              disabled={safePage === totalPages}
              className="px-3 py-1 rounded-lg border border-slate-300 bg-white text-slate-600 hover:bg-slate-100 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Feedback Detail Dialog */}
      {selectedFeedback && (
        <Dialog open={!!selectedFeedback} onOpenChange={() => setSelectedFeedback(null)}>
          <DialogContent className="bg-white max-w-4xl">
            <DialogHeader>
              <DialogTitle className="text-[#721C24] text-2xl">
                Feedback #{selectedFeedback.complaint_id}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <p className="text-xs text-gray-500">Source: {videoSrc || 'no video path found'}</p>
              {videoSrc ? (
                <div className="bg-slate-900 rounded-lg overflow-hidden aspect-video relative">
                  <video
                    id="officer-feedback-video"
                    src={videoSrc}
                    controls
                    className="w-full h-full object-cover"
                    onEnded={() => setVideoPlaying(false)}
                    onPlay={() => setVideoPlaying(true)}
                    onPause={() => setVideoPlaying(false)}
                    onError={() => toast.error('Video playback failed. Please try again.')}
                  />
                  {!videoPlaying && (
                    <button
                      onClick={() => {
                        const videoEl = document.getElementById('officer-feedback-video');
                        if (videoEl && typeof videoEl.play === 'function') {
                          videoEl.play();
                          setVideoPlaying(true);
                        }
                      }}
                      className="absolute inset-0 m-auto flex items-center justify-center bg-black/30 text-white text-lg font-semibold px-5 py-3 rounded-lg"
                      style={{ maxWidth: '240px' }}
                    >
                      ▶ Play Video
                    </button>
                  )}
                </div>
              ) : (
                <div className="bg-slate-900 rounded-lg overflow-hidden aspect-video flex items-center justify-center">
                  <span className="text-white">Video not available</span>
                </div>
              )}

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-[#4A5568]">Devotee</p>
                  <p className="font-medium">{selectedFeedback.user_name}</p>
                  <p className="text-sm">{selectedFeedback.user_mobile}</p>
                </div>
                <div>
                  <p className="text-sm text-[#4A5568]">Service</p>
                  <p className="font-medium">{selectedFeedback.service}</p>
                </div>
                <div>
                  <p className="text-sm text-[#4A5568]">Rating</p>
                  {renderStars(selectedFeedback.rating)}
                </div>
                <div>
                  <p className="text-sm text-[#4A5568]">Date</p>
                  <p className="font-medium">
                    {format(new Date(selectedFeedback.created_at), 'MMM dd, yyyy HH:mm')}
                  </p>
                </div>
              </div>

              {selectedFeedback.message && (
                <div>
                  <p className="text-sm text-[#4A5568] mb-1">Devotee Message</p>
                  <p className="text-[#1A202C] bg-[#FFF9E6] p-3 rounded-lg">
                    {selectedFeedback.message}
                  </p>
                </div>
              )}

              <div>
                <label className="text-sm text-[#721C24] font-medium mb-2 block">
                  Update Status
                </label>
                <Select value={statusUpdate} onValueChange={setStatusUpdate}>
                  <SelectTrigger data-testid="status-update-select">
                    <SelectValue placeholder="Select status" />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    <SelectItem value="Pending">Pending</SelectItem>
                    <SelectItem value="In Progress">In Progress</SelectItem>
                    <SelectItem value="Resolved">Resolved</SelectItem>
                    <SelectItem value="Rejected">Rejected</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div>
                <label className="text-sm text-[#721C24] font-medium mb-2 block">
                  Officer Notes *
                </label>
                <Textarea
                  value={officerNotes}
                  onChange={(e) => setOfficerNotes(e.target.value)}
                  data-testid="officer-notes-textarea"
                  placeholder="Add notes or response..."
                  rows={3}
                  className="border-[#E2E8F0]"
                />
              </div>

              <Button
                onClick={handleStatusUpdate}
                data-testid="update-status-button"
                className="w-full bg-[#721C24] hover:bg-[#5A161C] text-white py-6"
              >
                Update Status & Send WhatsApp
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default OfficerDashboard;