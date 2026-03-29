import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { format } from 'date-fns';
import jsPDF from 'jspdf';
import autoTable from 'jspdf-autotable';
import { toast } from 'sonner';
import { Download, FileText } from 'lucide-react';

const Reports = () => {
  const [feedback, setFeedback] = useState([]);
  const [temples, setTemples] = useState([]);
  const [filterTemple, setFilterTemple] = useState('all');
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage] = useState(5);

  const loadImageAsDataURL = async (url) => {
    const response = await fetch(url);
    if (!response.ok) throw new Error('Failed to load image');
    const blob = await response.blob();
    return await new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onloadend = () => resolve(reader.result);
      reader.onerror = reject;
      reader.readAsDataURL(blob);
    });
  };

  useEffect(() => {
    fetchFeedback();
    fetchTemples();
  }, []);

  const fetchFeedback = async () => {
    try {
      const params = {};
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
    fetchFeedback();
  }, [filterTemple]);

  useEffect(() => {
    setCurrentPage(1);
  }, [filterTemple]);

  const downloadPDF = async () => {
    const doc = new jsPDF();

    const pageWidth = doc.internal.pageSize.getWidth();
    const pageHeight = doc.internal.pageSize.getHeight();

    // Header (logo + name) using actual logo if available
    const logoHeight = 18;
    const logoWidth = 18;
    const logoX = 14;
    const logoY = 8;

    try {
      const logoData = await loadImageAsDataURL('/ts-logo.png');
      doc.addImage(logoData, 'PNG', logoX, logoY, logoWidth, logoHeight);
    } catch {
      doc.setDrawColor(33, 150, 83);
      doc.circle(logoX + logoWidth / 2, logoY + logoHeight / 2, logoWidth / 2, 'S');
      doc.setFontSize(7);
      doc.setTextColor(255, 255, 255);
      doc.text('GT', logoX + logoWidth / 2, logoY + logoHeight / 2 + 1.5, { align: 'center' });
    }

    doc.setFontSize(16);
    doc.setTextColor(0, 105, 38);
    doc.text('Government of Telangana', pageWidth / 2, 16, { align: 'center' });

    doc.setFontSize(12);
    doc.setTextColor(148, 15, 20);
    doc.text('Endowment Department', pageWidth / 2, 22, { align: 'center' });

    doc.setDrawColor(114, 28, 36);
    doc.setLineWidth(0.5);
    doc.line(14, 25, pageWidth - 14, 25);

    doc.setFontSize(18);
    doc.setTextColor(114, 28, 36);
    doc.text('Temple Feedback Report', pageWidth / 2, 30, { align: 'center' });

    // Subheader
    if (filterTemple !== 'all') {
      const temple = temples.find(t => t.id === filterTemple);
      doc.setFontSize(10);
      doc.setTextColor(74, 85, 104);
      doc.text(`Temple: ${temple?.name || 'All'}`, pageWidth / 2, 36, { align: 'center' });
    }

    doc.setFontSize(10);
    doc.setTextColor(74, 85, 104);
    doc.text(`Generated on: ${format(new Date(), 'MMMM dd, yyyy HH:mm')}`, pageWidth / 2, 42, { align: 'center' });

    // Footer content function used after table render
    const addFooter = (pageNumber, pageCount) => {
      doc.setFontSize(8);
      doc.setTextColor(99, 115, 129);
      doc.text('Developed by Aatreya Infotech', 14, pageHeight - 10);
      doc.text(`Page ${pageNumber} of ${pageCount}`, pageWidth - 14, pageHeight - 10, { align: 'right' });
    };

    // Table
    const tableData = feedback.map((item) => [
      item.complaint_id,
      item.temple_name,
      item.user_name,
      item.service,
      item.rating + '/5',
      item.status,
      format(new Date(item.created_at), 'MMM dd, yyyy'),
    ]);

    autoTable(doc, {
      head: [['ID', 'Temple', 'Devotee', 'Service', 'Rating', 'Status', 'Date']],
      body: tableData,
      startY: 48,
      theme: 'striped',
      headStyles: {
        fillColor: [114, 28, 36],
        textColor: [255, 255, 255],
      },
      styles: {
        fontSize: 8,
      },
      didDrawPage: (data) => {
        const pageNumber = doc.internal.getNumberOfPages();
        addFooter(pageNumber, pageNumber);
      },
    });

    const pageCount = doc.internal.getNumberOfPages();
    for (let i = 1; i <= pageCount; i += 1) {
      doc.setPage(i);
      addFooter(i, pageCount);
    }

    doc.save(`temple-feedback-report-${format(new Date(), 'yyyy-MM-dd')}.pdf`);
    toast.success('PDF downloaded successfully');
  };

  const downloadCSV = () => {
    const headers = ['ID', 'Temple', 'Devotee Name', 'Mobile', 'Service', 'Rating', 'Status', 'Message', 'Date'];
    const rows = feedback.map((item) => [
      item.complaint_id,
      item.temple_name,
      item.user_name,
      item.user_mobile,
      item.service,
      item.rating,
      item.status,
      item.message || '',
      format(new Date(item.created_at), 'yyyy-MM-dd HH:mm'),
    ]);

    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.map((cell) => `"${cell}"`).join(',')),
    ].join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `temple-feedback-report-${format(new Date(), 'yyyy-MM-dd')}.csv`;
    a.click();
    window.URL.revokeObjectURL(url);
    toast.success('CSV downloaded successfully');
  };

  if (loading) {
    return <div className="text-center py-8">Loading...</div>;
  }

  const stats = {
    total: feedback.length,
    pending: feedback.filter((f) => f.status === 'Pending').length,
    inProgress: feedback.filter((f) => f.status === 'In Progress').length,
    resolved: feedback.filter((f) => f.status === 'Resolved').length,
    rejected: feedback.filter((f) => f.status === 'Rejected').length,
    avgRating: feedback.length > 0
      ? (feedback.reduce((sum, f) => sum + f.rating, 0) / feedback.length).toFixed(1)
      : 0,
  };

  const totalPages = Math.max(1, Math.ceil(feedback.length / rowsPerPage));
  const pagedFeedback = feedback.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);
  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > totalPages) return;
    setCurrentPage(newPage);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-2">Reports</h1>
        <p className="text-[#4A5568]">Generate and download feedback reports</p>
      </div>

      {/* Filters and Export */}
      <div className="flex items-center justify-between bg-white p-4 rounded-xl">
        <div className="w-64">
          <Select value={filterTemple} onValueChange={setFilterTemple}>
            <SelectTrigger data-testid="report-temple-filter">
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

        <div className="flex gap-3">
          <Button
            onClick={downloadPDF}
            data-testid="download-pdf-button"
            className="bg-[#721C24] hover:bg-[#5A161C] text-white"
          >
            <FileText size={18} className="mr-2" />
            Export PDF
          </Button>
          <Button
            onClick={downloadCSV}
            data-testid="download-csv-button"
            className="bg-[#F4C430] hover:bg-[#D4A825] text-[#721C24]"
          >
            <Download size={18} className="mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <div className="bg-white p-6 rounded-xl border-t-2 border-t-[#721C24]">
          <p className="text-sm uppercase tracking-wider text-slate-500 mb-1">Total</p>
          <p className="text-3xl font-bold text-[#721C24]">{stats.total}</p>
        </div>
        <div className="bg-white p-6 rounded-xl border-t-2 border-t-[#DD6B20]">
          <p className="text-sm uppercase tracking-wider text-slate-500 mb-1">Pending</p>
          <p className="text-3xl font-bold text-[#DD6B20]">{stats.pending}</p>
        </div>
        <div className="bg-white p-6 rounded-xl border-t-2 border-t-[#2B6CB0]">
          <p className="text-sm uppercase tracking-wider text-slate-500 mb-1">In Progress</p>
          <p className="text-3xl font-bold text-[#2B6CB0]">{stats.inProgress}</p>
        </div>
        <div className="bg-white p-6 rounded-xl border-t-2 border-t-[#1E7E34]">
          <p className="text-sm uppercase tracking-wider text-slate-500 mb-1">Resolved</p>
          <p className="text-3xl font-bold text-[#1E7E34]">{stats.resolved}</p>
        </div>
        <div className="bg-white p-6 rounded-xl border-t-2 border-t-[#C53030]">
          <p className="text-sm uppercase tracking-wider text-slate-500 mb-1">Rejected</p>
          <p className="text-3xl font-bold text-[#C53030]">{stats.rejected}</p>
        </div>
        <div className="bg-white p-6 rounded-xl border-t-2 border-t-[#F4C430]">
          <p className="text-sm uppercase tracking-wider text-slate-500 mb-1">Avg Rating</p>
          <p className="text-3xl font-bold text-[#F4C430]">{stats.avgRating}</p>
        </div>
      </div>

      {/* Recent Feedback Preview */}
      <div className="bg-white p-6 rounded-xl">
        <h2 className="text-2xl font-semibold text-[#721C24] mb-4">Recent Feedback Preview</h2>
        <div className="space-y-3">
          {pagedFeedback.map((item) => (
            <div
              key={item.id}
              className="flex items-center justify-between p-4 bg-[#FDFBF7] rounded-lg"
            >
              <div className="flex-1">
                <p className="font-medium">{item.complaint_id} - {item.temple_name}</p>
                <p className="text-sm text-[#4A5568]">{item.user_name} • {item.service}</p>
              </div>
              <div className="flex items-center gap-4">
                <span className="text-sm font-medium">{item.rating}/5</span>
                <span
                  className={`px-3 py-1 rounded-full text-xs ${
                    item.status === 'Resolved'
                      ? 'bg-[#E6F4EA] text-[#1E7E34]'
                      : item.status === 'Pending'
                      ? 'bg-[#FFF4E5] text-[#DD6B20]'
                      : 'bg-[#E6F4FF] text-[#2B6CB0]'
                  }`}
                >
                  {item.status}
                </span>
              </div>
            </div>
          ))}
        </div>
        <div className="flex items-center justify-between p-4 mt-4 border-t border-slate-200">
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
    </div>
  );
};

export default Reports;