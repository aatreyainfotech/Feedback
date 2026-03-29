import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { API } from '../utils/api';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Textarea } from '../components/ui/textarea';
import { Camera, Video, X, Star, Upload } from 'lucide-react';
import { toast } from 'sonner';
import Header from '../components/Header';
import Footer from '../components/Footer';

const PublicFeedbackSubmit = () => {
  const navigate = useNavigate();
  const [temples, setTemples] = useState([]);
  const [registeredTemple, setRegisteredTemple] = useState(null);
  const [formData, setFormData] = useState({
    temple_id: '',
    user_name: '',
    user_mobile: '',
    service: '',
    rating: 0,
    message: '',
  });
  const [videoBlob, setVideoBlob] = useState(null);
  const [isRecording, setIsRecording] = useState(false);
  const [recordingTime, setRecordingTime] = useState(0);
  const [videoPreview, setVideoPreview] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [cameraPermissionDenied, setCameraPermissionDenied] = useState(false);
  const [submissionSuccess, setSubmissionSuccess] = useState(false);
  const [showSimpleSuccess, setShowSimpleSuccess] = useState(false);
  const [complaintId, setComplaintId] = useState('');
  const [services, setServices] = useState([]);
  const [faceDetected, setFaceDetected] = useState(false);
  const [faceDetectionSupported, setFaceDetectionSupported] = useState(true);

  const mediaRecorderRef = useRef(null);
  const videoStreamRef = useRef(null);
  const videoPreviewRef = useRef(null);
  const timerRef = useRef(null);
  const faceDetectionRafRef = useRef(null);
  const faceDetectionBusyRef = useRef(false);
  const faceDetectorRef = useRef(null);
  const detectionCanvasRef = useRef(null);

  const attachStreamToPreview = async (stream, retries = 10) => {
    const videoEl = videoPreviewRef.current;
    if (!videoEl) {
      if (retries <= 0) return;
      setTimeout(() => attachStreamToPreview(stream, retries - 1), 80);
      return;
    }

    videoEl.srcObject = stream;
    videoEl.muted = true;
    videoEl.playsInline = true;
    videoEl.autoplay = true;
    videoEl.setAttribute('playsinline', 'true');
    videoEl.setAttribute('muted', 'true');
    await videoEl.play().catch(() => {});
  };

  useEffect(() => {
    // Check if tablet is registered to a temple
    const registered = localStorage.getItem('registered_temple');
    if (registered) {
      const templeData = JSON.parse(registered);
      setRegisteredTemple(templeData);
      setFormData(prev => ({ ...prev, temple_id: templeData.id }));
    } else {
      // If not registered, redirect to setup page
      navigate('/setup-temple');
      return;
    }
    
    fetchTemples();
    fetchServices();
    return () => {
      stopRecording();
      if (videoStreamRef.current) {
        videoStreamRef.current.getTracks().forEach(track => track.stop());
      }
    };
  }, [navigate]);

  const stopFaceDetection = () => {
    if (faceDetectionRafRef.current) {
      cancelAnimationFrame(faceDetectionRafRef.current);
      faceDetectionRafRef.current = null;
    }
    faceDetectionBusyRef.current = false;
  };

  const startFaceDetection = async () => {
    if (!videoPreviewRef.current) return;

    if (!('FaceDetector' in window)) {
      setFaceDetectionSupported(false);
      return;
    }

    setFaceDetectionSupported(true);

    if (!faceDetectorRef.current) {
      try {
        faceDetectorRef.current = new window.FaceDetector({ maxDetectedFaces: 1 });
      } catch {
        setFaceDetectionSupported(false);
        return;
      }
    }

    stopFaceDetection();

    const detectLoop = async () => {
      const videoEl = videoPreviewRef.current;
      if (!videoEl || videoEl.readyState < 2 || videoEl.videoWidth === 0) {
        faceDetectionRafRef.current = requestAnimationFrame(detectLoop);
        return;
      }

      if (faceDetectionBusyRef.current) {
        faceDetectionRafRef.current = requestAnimationFrame(detectLoop);
        return;
      }

      faceDetectionBusyRef.current = true;
      try {
        const canvas = detectionCanvasRef.current;
        if (!canvas) {
          faceDetectionBusyRef.current = false;
          faceDetectionRafRef.current = requestAnimationFrame(detectLoop);
          return;
        }

        const ctx = canvas.getContext('2d', { willReadFrequently: true });
        if (ctx) {
          const targetWidth = 320;
          const ratio = videoEl.videoHeight > 0 ? (videoEl.videoHeight / videoEl.videoWidth) : (9 / 16);
          const targetHeight = Math.max(180, Math.round(targetWidth * ratio));
          canvas.width = targetWidth;
          canvas.height = targetHeight;
          ctx.drawImage(videoEl, 0, 0, targetWidth, targetHeight);
          const faces = await faceDetectorRef.current.detect(canvas);
          setFaceDetected(faces.length > 0);
        }
      } catch {
        setFaceDetectionSupported(false);
        stopFaceDetection();
        return;
      } finally {
        faceDetectionBusyRef.current = false;
      }

      faceDetectionRafRef.current = requestAnimationFrame(detectLoop);
    };

    faceDetectionRafRef.current = requestAnimationFrame(detectLoop);
  };

  const fetchServices = async () => {
    try {
      const response = await axios.get(`${API}/services`);
      setServices(response.data);
    } catch (error) {
      console.error('Failed to fetch services:', error);
      // Fallback to default services
      setServices([
        { id: '1', name: 'Annadhanam' },
        { id: '2', name: 'Darshan' },
        { id: '3', name: 'Prasadam' },
        { id: '4', name: 'Pooja' },
        { id: '5', name: 'Donation' },
        { id: '6', name: 'Other' },
        { id: '7', name: 'General' }
      ]);
    }
  };

  const fetchTemples = async () => {
    try {
      const response = await axios.get(`${API}/temples`);
      setTemples(response.data);
    } catch (error) {
      toast.error('Failed to fetch temples');
    }
  };

  const startRecording = async () => {
    try {
      setCameraPermissionDenied(false);
      setFaceDetected(false);
      
      // Request front camera (user-facing camera on mobile/tablet)
      let stream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: { ideal: 'user' },
            width: { ideal: 1280 },
            height: { ideal: 720 },
            aspectRatio: { ideal: 9 / 16 }
          },
          audio: true
        });
      } catch {
        // Fallback for older mobile/tablet browsers.
        stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: true });
      }
      
      videoStreamRef.current = stream;

      // Ensure the recording preview element is mounted before binding stream.
      setIsRecording(true);
      setRecordingTime(0);
      await attachStreamToPreview(stream);
      startFaceDetection();

      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'video/webm;codecs=vp8,opus'
      });
      
      const chunks = [];
      
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          chunks.push(e.data);
        }
      };
      
      mediaRecorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'video/webm' });

if (blob.size === 0) {
  toast.error("Video recording failed. Please try again.");
  return;
}
        setVideoBlob(blob);
        setVideoPreview(URL.createObjectURL(blob));
        
        if (videoStreamRef.current) {
          videoStreamRef.current.getTracks().forEach(track => track.stop());
        }
      };
      
      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      
      // Start timer
      timerRef.current = setInterval(() => {
        setRecordingTime(prev => {
          if (prev >= 60) {
            stopRecording();
            return 60;
          }
          return prev + 1;
        });
      }, 1000);
      
      // Auto-stop after 60 seconds
      setTimeout(() => {
        if (mediaRecorderRef.current?.state === 'recording') {
          stopRecording();
        }
      }, 60000);
      
    } catch (error) {
      console.error('Camera access error:', error);
      setCameraPermissionDenied(true);
      
      if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        toast.error('Camera access denied. Please enable camera permissions in your browser settings.', {
          duration: 6000
        });
      } else if (error.name === 'NotFoundError') {
        toast.error('No camera found on this device. Please check your device settings.', {
          duration: 6000
        });
      } else {
        toast.error('Failed to access camera. Please check your browser permissions.', {
          duration: 6000
        });
      }
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === 'recording') {
      mediaRecorderRef.current.stop();
    }
    setIsRecording(false);
    stopFaceDetection();
    if (timerRef.current) {
      clearInterval(timerRef.current);
    }
  };

  const clearVideo = () => {
    setVideoBlob(null);
    setVideoPreview(null);
    setRecordingTime(0);
    setFaceDetected(false);
    stopFaceDetection();
  };

  const clearForm = () => {
    setFormData({
      temple_id: registeredTemple?.id || '',
      user_name: '',
      user_mobile: '',
      service: '',
      rating: 0,
      message: '',
    });
    clearVideo();
    setSubmissionSuccess(false);
    setShowSimpleSuccess(false);
    setComplaintId('');
  };

  const handleBackToDisplay = () => {
    navigate('/display');
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!formData.temple_id || !formData.user_name || !formData.user_mobile || !formData.service || formData.rating === 0) {
      toast.error('Please fill all required fields');
      return;
    }

    if (formData.user_mobile.length !== 10) {
      toast.error('Please enter a valid 10-digit mobile number');
      return;
    }

    if (!videoBlob) {
      toast.error('Please record a video');
      return;
    }

    setSubmitting(true);

    try {
      // Upload video first
      const videoFormData = new FormData();
      videoFormData.append('file', videoBlob, 'feedback-video.webm');
      
      const uploadResponse = await axios.post(`${API}/upload/video`, videoFormData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      // Submit feedback with video path
      const feedbackResponse = await axios.post(`${API}/feedback`, {
        ...formData,
        video_url: uploadResponse.data.path,
      });

      // Show success screen
      setComplaintId(feedbackResponse.data.complaint_id);
      setSubmissionSuccess(true);
      
      // After 1 second, show the simple success screen
      setTimeout(() => {
        setShowSimpleSuccess(true);
      }, 1000);
      
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit feedback');
    } finally {
      setSubmitting(false);
    }
  };

  // Show success screen after submission
  if (submissionSuccess) {
    // Show simple success screen after 1 second
    if (showSimpleSuccess) {
      return (
        <div className="min-h-screen flex flex-col bg-[#FDFBF7]">
          <Header logo="/ts-logo.png" />
          
          <div 
            className="flex-1 bg-cover bg-center bg-no-repeat relative flex items-center justify-center"
            style={{
              backgroundImage: 'url(https://customer-assets.emergentagent.com/job_temple-feedback-1/artifacts/0cablq1w_image.png)',
              minHeight: 'calc(100vh - 180px)',
            }}
          >
            <div className="absolute inset-0 bg-black/50"></div>
          
            <div className="relative z-10 bg-white/95 backdrop-blur-sm rounded-3xl shadow-2xl p-12 max-w-xl w-full mx-4 text-center">
              {/* Temple Name */}
              <div className="bg-[#FFF9E6] p-8 rounded-2xl mb-8 border-2 border-[#F4C430]">
                <div className="flex items-center justify-center gap-4">
                  {registeredTemple?.logo_path && (
                    <img 
                      src={`${API}/files/${registeredTemple.logo_path}`}
                      alt={`${registeredTemple.name} logo`}
                      className="w-20 h-20 object-contain rounded-lg border-2 border-[#721C24]"
                    />
                  )}
                  <div>
                    <p className="text-3xl font-bold text-[#721C24]">
                      {registeredTemple?.name}
                    </p>
                    <p className="text-lg text-[#4A5568]">
                      {registeredTemple?.location}
                    </p>
                  </div>
                </div>
              </div>

              {/* Create New Feedback Button */}
              <Button
                onClick={clearForm}
                data-testid="create-new-feedback-button"
                className="w-full h-20 bg-[#721C24] hover:bg-[#5A161C] text-white text-2xl font-semibold rounded-xl border-4 border-white/30"
              >
                Create New Feedback
              </Button>
            </div>
          </div>
          
          <Footer />
        </div>
      );
    }

    // Show full success screen first (for 1 second)
    return (
      <div className="min-h-screen flex flex-col bg-[#FDFBF7]">
        <Header logo="/ts-logo.png" />
        
        <div 
          className="flex-1 bg-cover bg-center bg-no-repeat relative flex items-center justify-center"
          style={{
            backgroundImage: 'url(https://customer-assets.emergentagent.com/job_temple-feedback-1/artifacts/0cablq1w_image.png)',
            minHeight: 'calc(100vh - 180px)',
          }}
        >
          <div className="absolute inset-0 bg-black/50"></div>
        
        <div className="relative z-10 bg-white/95 backdrop-blur-sm rounded-3xl shadow-2xl p-12 max-w-2xl w-full mx-4 text-center">
          {/* Success Icon */}
          <div className="mb-6">
            <div className="w-32 h-32 bg-green-100 rounded-full mx-auto flex items-center justify-center">
              <svg className="w-20 h-20 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>

          {/* Success Message */}
          <h1 className="text-4xl font-bold text-[#721C24] mb-4">
            Successfully Submitted!
          </h1>
          <p className="text-2xl text-[#4A5568] mb-8">
            Thank you for visiting
          </p>

          {/* Temple Name */}
          <div className="bg-[#FFF9E6] p-6 rounded-2xl mb-6 border-2 border-[#F4C430]">
            <div className="flex items-center justify-center gap-4 mb-3">
              {registeredTemple?.logo_path && (
                <img 
                  src={`${API}/files/${registeredTemple.logo_path}`}
                  alt={`${registeredTemple.name} logo`}
                  className="w-16 h-16 object-contain rounded-lg border-2 border-[#721C24]"
                />
              )}
              <div>
                <p className="text-3xl font-bold text-[#721C24]">
                  {registeredTemple?.name}
                </p>
                <p className="text-lg text-[#4A5568]">
                  {registeredTemple?.location}
                </p>
              </div>
            </div>
          </div>

          {/* Transaction ID */}
          <div className="bg-[#721C24] text-white p-8 rounded-2xl mb-8">
            <p className="text-lg mb-2">Your Transaction ID</p>
            <p className="text-5xl font-bold tracking-wider" data-testid="transaction-id">
              {complaintId}
            </p>
          </div>

          {/* Action Buttons */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Button
              onClick={handleBackToDisplay}
              data-testid="back-to-display-button"
              className="h-16 bg-[#F4C430] hover:bg-[#D4A825] text-[#721C24] text-lg font-semibold"
            >
              Back to Display
            </Button>
            <Button
              onClick={clearForm}
              data-testid="clear-feedback-button"
              className="h-16 bg-[#721C24] hover:bg-[#5A161C] text-white text-lg font-semibold"
            >
              Create New Feedback
            </Button>
          </div>
        </div>
      </div>
      
      <Footer />
    </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-[#FDFBF7]">
      <Header logo="/ts-logo.png" />
      
      <div 
        className="flex-1 bg-cover bg-center bg-no-repeat relative"
        style={{
          backgroundImage: 'url(https://customer-assets.emergentagent.com/job_temple-feedback-1/artifacts/0cablq1w_image.png)',
          minHeight: 'calc(100vh - 180px)',
        }}
      >
        <div className="absolute inset-0 bg-black/50"></div>
      
      <div className="relative z-10 container mx-auto px-4 py-8 page-container">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-3xl sm:text-5xl font-bold text-[#F4C430] mb-2">Create Feedback</h1>
          <p className="text-base sm:text-xl text-white/90">Share your temple experience with us</p>
          {registeredTemple && (
            <div className="mt-6 inline-block bg-white/95 px-8 py-6 rounded-2xl shadow-2xl border-2 border-[#F4C430]">
              <div className="flex items-center gap-4">
                {registeredTemple.logo_path && (
                  <img 
                    src={`${API}/files/${registeredTemple.logo_path}`}
                    alt={`${registeredTemple.name} logo`}
                    className="w-20 h-20 object-contain rounded-lg border-2 border-[#721C24] shadow-md"
                  />
                )}
                <div className="text-left">
                  <p className="text-3xl font-bold text-[#721C24]">{registeredTemple.name}</p>
                  <p className="text-lg text-[#4A5568] mt-1">{registeredTemple.location}</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Form */}
        <div className="w-full max-w-2xl mx-auto bg-white/95 backdrop-blur-sm rounded-2xl shadow-2xl p-4 sm:p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="global-center">
              <p className="text-sm text-[#721C24]">Please position your device to center the video and ensure consistent feedback recording.</p>
            </div>
            {/* Temple Selection - Hidden if registered */}
            {!registeredTemple && (
              <div>
                <Label className="text-[#721C24] font-medium text-lg">Select Temple *</Label>
                <Select
                  value={formData.temple_id}
                  onValueChange={(value) => setFormData({ ...formData, temple_id: value })}
                >
                  <SelectTrigger 
                    data-testid="public-temple-select"
                    className="mt-2 h-12 border-2 border-[#E2E8F0] focus:border-[#721C24]"
                  >
                    <SelectValue placeholder="Choose a temple" />
                  </SelectTrigger>
                  <SelectContent className="bg-white">
                    {temples.map((temple) => (
                      <SelectItem key={temple.id} value={temple.id}>
                        {temple.name}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}

            {/* Name */}
            <div>
              <Label className="text-[#721C24] font-medium text-lg">Devotee Name *</Label>
              <Input
                value={formData.user_name}
                onChange={(e) => setFormData({ ...formData, user_name: e.target.value })}
                data-testid="devotee-name-input"
                placeholder="Enter your name"
                className="mt-2 h-12 border-2 border-[#E2E8F0] focus:border-[#721C24]"
                required
              />
            </div>

            {/* Mobile Number */}
            <div>
              <Label className="text-[#721C24] font-medium text-lg">Mobile Number *</Label>
              <Input
                type="tel"
                value={formData.user_mobile}
                onChange={(e) => {
                  const value = e.target.value.replace(/\D/g, '').slice(0, 10);
                  setFormData({ ...formData, user_mobile: value });
                }}
                data-testid="devotee-mobile-input"
                placeholder="Enter 10-digit mobile number"
                pattern="[0-9]{10}"
                maxLength={10}
                className="mt-2 h-12 border-2 border-[#E2E8F0] focus:border-[#721C24] text-lg tracking-wider"
                required
              />
              <p className="text-sm text-[#4A5568] mt-1">
                {formData.user_mobile.length}/10 digits
              </p>
            </div>

            {/* Select Service */}
            <div>
              <Label className="text-[#721C24] font-medium text-lg">Select Service *</Label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 mt-3">
                {services.map((service) => {
                  const serviceIcons = {
                    'Annadhanam': '🍚',
                    'Darshan': '🙏',
                    'Prasadam': '🍲',
                    'Pooja': '🪔',
                    'Donation': '💰',
                    'Other': '📝',
                    'General': '📋',
                    'Seva': '🙏',
                    'Archana': '🌸',
                    'Abhishekam': '💧',
                    'Homam': '🔥',
                    'Marriage': '💍',
                    'Blessing': '✨',
                    'Priest': '👳',
                    'Pujari': '👳',
                    'Temple': '🛕',
                    'Ticket': '🎫',
                    'VIP': '⭐',
                    'Queue': '📊',
                    'Accommodation': '🏨',
                    'Parking': '🅿️',
                    'Laddu': '🍪',
                    'Flowers': '💐',
                    'Kalyanam': '💒',
                    'Annaprasana': '🍼',
                    'Naamkaran': '📜',
                    'Upanayanam': '📿',
                    'Satyanarayana': '🙏',
                    'Ganapathi': '🐘',
                    'Lakshmi': '🪷',
                    'Vishnu': '🔱',
                    'Shiva': '🕉️'
                  };
                  const icon = serviceIcons[service.name] || '📋';
                  
                  return (
                    <button
                      key={service.id}
                      type="button"
                      onClick={() => setFormData({ ...formData, service: service.name })}
                      data-testid={`service-${service.name.toLowerCase()}`}
                      className={`relative p-4 rounded-xl border-2 transition-all duration-300 font-semibold text-center group ${
                        formData.service === service.name
                          ? 'bg-gradient-to-br from-[#721C24] to-[#8B2830] text-white border-[#721C24] shadow-lg scale-[1.02]'
                          : 'bg-white text-[#721C24] border-[#E8D5B7] hover:border-[#721C24] hover:shadow-md hover:scale-[1.01]'
                      }`}
                    >
                      <div className="text-2xl mb-1">{icon}</div>
                      <div className="text-sm">{service.name}</div>
                      {formData.service === service.name && (
                        <div className="absolute top-1 right-1 w-5 h-5 bg-[#F4C430] rounded-full flex items-center justify-center">
                          <svg className="w-3 h-3 text-[#721C24]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                          </svg>
                        </div>
                      )}
                    </button>
                  );
                })}
                
              </div>
            </div>

            {/* Select Rating */}
            <div>
              <Label className="text-[#721C24] font-medium text-lg">Select Rating *</Label>
              <div className="flex gap-2 mt-2">
                {[1, 2, 3, 4, 5].map((star) => (
                  <button
                    key={star}
                    type="button"
                    onClick={() => setFormData({ ...formData, rating: star })}
                    data-testid={`rating-${star}`}
                    className="transition-transform hover:scale-110"
                  >
                    <Star
                      size={48}
                      className={
                        star <= formData.rating
                          ? 'fill-[#F4C430] text-[#F4C430]'
                          : 'text-gray-300'
                      }
                    />
                  </button>
                ))}
              </div>
            </div>

            {/* Video Recording */}
            <div>
              <Label className="text-[#721C24] font-medium text-lg">
                Record Video (Max 60 seconds) *
              </Label>
              
              <div className="mt-2 border-4 border-dashed border-[#E2E8F0] rounded-xl p-6 bg-[#FDFBF7] flex flex-col items-center justify-center">
                {!videoPreview && !isRecording && (
                  <div className="text-center space-y-4 w-full max-w-md">
                    <Camera className="mx-auto text-[#721C24]" size={64} />
                    <Button
                      type="button"
                      onClick={startRecording}
                      data-testid="start-recording-button"
                      className="w-full bg-[#721C24] hover:bg-[#5A161C] text-white text-lg px-8 py-6"
                    >
                      <Video size={24} className="mr-2" />
                      Start Recording
                    </Button>
                    <p className="text-sm text-[#4A5568]">
                      📹 Uses front camera on mobile/tablet
                    </p>
                    
                    {cameraPermissionDenied && (
                      <div className="mt-4 p-4 bg-red-50 border-2 border-red-200 rounded-lg text-left">
                        <p className="text-red-800 font-semibold mb-2">📷 Camera Permission Required</p>
                        <p className="text-sm text-red-700 mb-3">
                          Please allow camera access to record video:
                        </p>
                        <div className="space-y-2 text-sm text-red-700">
                          <div className="bg-white p-3 rounded border border-red-200">
                            <p className="font-semibold">🖥️ Desktop (Chrome/Edge):</p>
                            <p>1. Click the 🔒 lock icon in address bar</p>
                            <p>2. Click "Camera" → Select "Allow"</p>
                            <p>3. Refresh page</p>
                          </div>
                          
                          <div className="bg-white p-3 rounded border border-red-200">
                            <p className="font-semibold">🦊 Firefox:</p>
                            <p>1. Click the 📷 camera icon in address bar</p>
                            <p>2. Click "Allow"</p>
                            <p>3. Refresh page</p>
                          </div>
                          
                          <div className="bg-white p-3 rounded border border-red-200">
                            <p className="font-semibold">📱 Mobile/Tablet:</p>
                            <p>1. Go to Settings → Apps → Browser</p>
                            <p>2. Tap Permissions → Camera → Allow</p>
                            <p>3. Return and refresh page</p>
                          </div>
                        </div>
                        <Button
                          type="button"
                          onClick={startRecording}
                          className="w-full mt-4 bg-[#721C24] hover:bg-[#5A161C] text-white"
                        >
                          Try Again
                        </Button>
                      </div>
                    )}
                  </div>
                )}

                {isRecording && (
                  <div className="space-y-4 mx-auto w-full max-w-2xl py-4 bg-black/10 rounded-xl border border-[#721C24]">
                    <div className="w-full relative overflow-hidden rounded-lg bg-black">
                      <video
                        ref={videoPreviewRef}
                        autoPlay
                        muted
                        playsInline
                        className="w-full h-64 object-cover"
                        onLoadedMetadata={() => {
                          videoPreviewRef.current?.play().catch(() => {});
                        }}
                      />
                      <div className="absolute inset-0 flex items-center justify-center bg-black/20">
                        <span className="text-white text-lg font-bold">Recording: {recordingTime}s</span>
                      </div>
                    </div>
                    <canvas ref={detectionCanvasRef} className="hidden" aria-hidden="true" />
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-4 h-4 bg-red-600 rounded-full animate-pulse"></div>
                        <span className="text-2xl font-bold text-[#721C24]">
                          {recordingTime}s / 60s
                        </span>
                        <span className={`text-sm font-semibold px-2 py-1 rounded ${faceDetected ? 'bg-green-100 text-green-700' : 'bg-amber-100 text-amber-700'}`}>
                          {faceDetectionSupported ? (faceDetected ? 'Face detected' : 'Face not detected') : 'Face detection not supported'}
                        </span>
                      </div>
                      <Button
                        type="button"
                        onClick={stopRecording}
                        data-testid="stop-recording-button"
                        className="bg-red-600 hover:bg-red-700 text-white"
                      >
                        Stop Recording
                      </Button>
                    </div>
                  </div>
                )}

                {videoPreview && !isRecording && (
                  <div className="space-y-4 mx-auto w-full max-w-2xl py-4 bg-black/10 rounded-xl border border-[#721C24]">
                    <video
                      src={videoPreview}
                      controls
                      className="w-full h-64 rounded-lg bg-black object-cover"
                    />
                    <div className="flex gap-3">
                      <Button
                        type="button"
                        onClick={clearVideo}
                        data-testid="clear-video-button"
                        variant="outline"
                        className="flex-1 border-2 border-[#721C24] text-[#721C24] hover:bg-[#721C24] hover:text-white"
                      >
                        <X size={20} className="mr-2" />
                        Clear Video
                      </Button>
                      <Button
                        type="button"
                        onClick={startRecording}
                        className="flex-1 bg-[#F4C430] hover:bg-[#D4A825] text-[#721C24]"
                      >
                        <Video size={20} className="mr-2" />
                        Re-record
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Message (Optional) */}
            <div>
              <Label className="text-[#721C24] font-medium text-lg">
                Additional Message (Optional)
              </Label>
              <Textarea
                value={formData.message}
                onChange={(e) => setFormData({ ...formData, message: e.target.value })}
                data-testid="feedback-message-textarea"
                placeholder="Share more details about your experience..."
                rows={4}
                className="mt-2 border-2 border-[#E2E8F0] focus:border-[#721C24]"
              />
            </div>

            {/* Action Buttons */}
            <div className="flex gap-4 pt-4">
              <Button
                type="button"
                onClick={clearForm}
                data-testid="clear-form-button"
                variant="outline"
                className="flex-1 h-14 border-2 border-[#721C24] text-[#721C24] hover:bg-[#721C24] hover:text-white text-lg"
              >
                Clear
              </Button>
              <Button
                type="submit"
                disabled={submitting}
                data-testid="submit-feedback-button"
                className="flex-1 h-14 bg-[#721C24] hover:bg-[#5A161C] text-white text-lg"
              >
                {submitting ? 'Submitting...' : 'Submit Feedback'}
              </Button>
            </div>
          </form>
        </div>
      </div>
      </div>
      
      <Footer />
    </div>
  );
};

export default PublicFeedbackSubmit;