import { useState, useEffect } from 'react';
import api from '../utils/api';
import { API } from '../utils/api';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Button } from '../components/ui/button';
import { Star, Play, UserPlus } from 'lucide-react';
import { format } from 'date-fns';
import { toast } from 'sonner';

const FeedbackMonitoring = () => {
  const [feedback, setFeedback] = useState([]);
  const [temples, setTemples] = useState([]);
  const [officers, setOfficers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedFeedback, setSelectedFeedback] = useState(null);
  const [assigningFeedback, setAssigningFeedback] = useState(null);
  const [selectedOfficer, setSelectedOfficer] = useState('');
  const [videoPlaying, setVideoPlaying] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');

  const videoPath = (selectedFeedback?.video_path || selectedFeedback?.video_url || '').replace(/^\/+/, '');
  const encodedVideoPath = videoPath ? videoPath.split('/').map(encodeURIComponent).join('/') : '';
  const videoSrc = encodedVideoPath ? `${API}/files/${encodedVideoPath}` : null;

  useEffect(() => {
    setVideoPlaying(false);
  }, [selectedFeedback]);
  const [filterTemple, setFilterTemple] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage] = useState(5);

  useEffect(() => {
    fetchFeedback();
    fetchTemples();
    fetchOfficers();
  }, []);

  const fetchOfficers = async () => {
    try {
      const response = await api.get('/officers');
      setOfficers(response.data);
    } catch (error) {
      console.error('Failed to fetch officers');
    }
  };

  const fetchFeedback = async () => {
    try {
      const params = {};
      if (filterStatus !== 'all') params.status = filterStatus;
      if (filterTemple !== 'all') params.temple_id = filterTemple;
      
      const response = await api.get('/feedback', { params });
      setFeedback(response.data);
    } catch (error) {
      toast.error('Failed to fetch feedback');
    } finally {
      setLoading(false);
    }
  };

  const fetchTemples = async () => {
    try {
      const response = await api.get('/temples');
      setTemples(response.data);
    } catch (error) {
      console.error('Failed to fetch temples');
    }
  };

  useEffect(() => {
    setCurrentPage(1);
    fetchFeedback();
  }, [filterStatus, filterTemple]);

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

  const totalPages = Math.max(1, Math.ceil(feedback.length / rowsPerPage));
  const pagedFeedback = feedback.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);

  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > totalPages) return;
    setCurrentPage(newPage);
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

  const handleAssignOfficer = async () => {
    if (!selectedOfficer) {
      toast.error('Please select an officer');
      return;
    }

    try {
      await api.put(`/feedback/${assigningFeedback.id}/assign`, {
        officer_id: selectedOfficer
      });
      toast.success('Officer assigned successfully');
      setAssigningFeedback(null);
      setSelectedOfficer('');
      fetchFeedback();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to assign officer');
    }
  };

  if (loading) {
    return <div className="text-center py-8">Loading...</div>;
  }

  return (
    <div className="space-y-6 feedback-page">
      <div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-2">Feedback Monitoring</h1>
        <p className="text-[#4A5568]">View and monitor all temple feedback</p>
      </div>

      {/* Filters */}
      <div className="flex gap-4 bg-white p-4 rounded-xl">
        <div className="w-48">
          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger data-testid="status-filter">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent className="bg-white">
              <SelectItem value="all">All Status</SelectItem>
              <SelectItem value="Pending">Pending</SelectItem>
              <SelectItem value="In Progress">In Progress</SelectItem>
              <SelectItem value="Resolved">Resolved</SelectItem>
              <SelectItem value="Rejected">Rejected</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="w-64">
          <Select value={filterTemple} onValueChange={setFilterTemple}>
            <SelectTrigger data-testid="temple-filter">
              <SelectValue placeholder="Filter by temple" />
            </SelectTrigger>
            <SelectContent className="bg-white">
              <SelectItem value="all">All Temples</SelectItem>
              {temples.map((temple) => (
                <SelectItem key={temple.id} value={temple.id}>
                  {temple.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {/* Feedback Table */}
      <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#FDFBF7] hover:bg-[#FDFBF7]">
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                ID
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Temple
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
                data-testid={`feedback-row-${item.id}`}
                className="hover:bg-[#FFF9E6] transition-colors"
              >
                <TableCell className="font-medium">{item.complaint_id}</TableCell>
                <TableCell className="text-[#4A5568]">{item.temple_name}</TableCell>
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
                  {item.video_path ? (
                    <button
                      onClick={() => setSelectedFeedback(item)}
                      data-testid={`play-video-${item.id}`}
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
                    onClick={() => {
                      setAssigningFeedback(item);
                      setSelectedOfficer(item.assigned_officer_id || '');
                    }}
                    data-testid={`assign-officer-${item.id}`}
                    className="bg-[#F4C430] hover:bg-[#D4A825] text-[#721C24]"
                  >
                    <UserPlus size={16} className="mr-1" />
                    {item.assigned_officer_name ? 'Reassign' : 'Assign'}
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        </div>
        <div className="flex items-center justify-between p-4 bg-white border-t border-slate-200">
          <div className="text-sm text-slate-500">
            Showing {Math.min((currentPage - 1) * rowsPerPage + 1, feedback.length)} - {Math.min(currentPage * rowsPerPage, feedback.length)} of {feedback.length}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => handlePageChange(currentPage - 1)}
              disabled={currentPage === 1}
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
                  className={`px-3 py-1 rounded-lg border ${page === currentPage ? 'border-[#721C24] bg-[#721C24] text-white' : 'border-slate-300 bg-white text-slate-700 hover:bg-slate-100'}`}
                >
                  {page}
                </button>
              );
            })}
            <button
              onClick={() => handlePageChange(currentPage + 1)}
              disabled={currentPage === totalPages}
              className="px-3 py-1 rounded-lg border border-slate-300 bg-white text-slate-600 hover:bg-slate-100 disabled:opacity-50"
            >
              Next
            </button>
          </div>
        </div>
      </div>

      {/* Video Player Dialog */}
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
              <div className="bg-slate-900 rounded-lg overflow-hidden aspect-video relative">
                {videoSrc ? (
                  <>
                    <video
                      id="feedback-video"
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
                          const videoEl = document.getElementById('feedback-video');
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
                  </>
                ) : (
                  <div className="text-center text-white p-6">Video not available</div>
                )}
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-[#4A5568]">Temple</p>
                  <p className="font-medium">{selectedFeedback.temple_name}</p>
                </div>
                <div>
                  <p className="text-sm text-[#4A5568]">Service</p>
                  <p className="font-medium">{selectedFeedback.service}</p>
                </div>
                <div>
                  <p className="text-sm text-[#4A5568]">Devotee</p>
                  <p className="font-medium">{selectedFeedback.user_name}</p>
                  <p className="text-sm">{selectedFeedback.user_mobile}</p>
                </div>
                <div>
                  <p className="text-sm text-[#4A5568]">Rating</p>
                  {renderStars(selectedFeedback.rating)}
                </div>
                {selectedFeedback.assigned_officer_name && (
                  <div>
                    <p className="text-sm text-[#4A5568]">Assigned Officer</p>
                    <p className="font-medium text-[#1E7E34]">{selectedFeedback.assigned_officer_name}</p>
                  </div>
                )}
              </div>
              {selectedFeedback.message && (
                <div>
                  <p className="text-sm text-[#4A5568] mb-1">Message</p>
                  <p className="text-[#1A202C]">{selectedFeedback.message}</p>
                </div>
              )}
              {selectedFeedback.officer_notes && (
                <div>
                  <p className="text-sm text-[#4A5568] mb-1">Officer Notes</p>
                  <p className="text-[#1A202C] bg-[#FFF9E6] p-3 rounded-lg">
                    {selectedFeedback.officer_notes}
                  </p>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Assign Officer Dialog */}
      {assigningFeedback && (
        <Dialog open={!!assigningFeedback} onOpenChange={() => setAssigningFeedback(null)}>
          <DialogContent className="bg-white">
            <DialogHeader>
              <DialogTitle className="text-[#721C24] text-2xl">
                Assign Officer to #{assigningFeedback.complaint_id}
              </DialogTitle>
            </DialogHeader>
            <div className="space-y-4">
              <div>
                <p className="text-sm text-[#4A5568] mb-2">Temple: {assigningFeedback.temple_name}</p>
                <p className="text-sm text-[#4A5568] mb-2">Devotee: {assigningFeedback.user_name}</p>
                {assigningFeedback.assigned_officer_name && (
                  <p className="text-sm text-[#1E7E34] mb-4">
                    Current: {assigningFeedback.assigned_officer_name}
                  </p>
                )}
              </div>
              
              <div>
                <label className="text-sm text-[#721C24] font-medium mb-2 block">
                  Select Officer
                </label>
                <Select value={selectedOfficer} onValueChange={setSelectedOfficer}>
                  <SelectTrigger data-testid="officer-select">
                    <SelectValue placeholder="Choose officer" />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    {officers.map((officer) => (
                      <SelectItem key={officer.id} value={officer.id}>
                        {officer.name} {officer.temple_name ? `(${officer.temple_name})` : ''}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              <Button
                onClick={handleAssignOfficer}
                data-testid="confirm-assign-button"
                className="w-full bg-[#721C24] hover:bg-[#5A161C] text-white py-6"
              >
                Assign Officer
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </div>
  );
};

export default FeedbackMonitoring;