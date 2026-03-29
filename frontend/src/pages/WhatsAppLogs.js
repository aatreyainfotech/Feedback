import { useState, useEffect } from 'react';
import api from '../utils/api';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../components/ui/table';
import { format } from 'date-fns';
import { toast } from 'sonner';
import { CheckCircle, XCircle } from 'lucide-react';

const WhatsAppLogs = () => {
  const [logs, setLogs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage] = useState(5);

  useEffect(() => {
    fetchLogs();
  }, []);

  const fetchLogs = async () => {
    try {
      const response = await api.get('/whatsapp/logs');
      setLogs(response.data);
    } catch (error) {
      toast.error('Failed to fetch WhatsApp logs');
    } finally {
      setLoading(false);
    }
  };

  const totalPages = Math.max(1, Math.ceil(logs.length / rowsPerPage));
  const pagedLogs = logs.slice((currentPage - 1) * rowsPerPage, currentPage * rowsPerPage);
  const handlePageChange = (newPage) => {
    if (newPage < 1 || newPage > totalPages) return;
    setCurrentPage(newPage);
  };

  if (loading) {
    return <div className="text-center py-8">Loading...</div>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-4xl sm:text-5xl font-bold tracking-tight mb-2">WhatsApp Logs</h1>
        <p className="text-[#4A5568]">View all WhatsApp message delivery logs</p>
      </div>

      <div className="bg-white rounded-2xl shadow-sm overflow-hidden">
        <Table>
          <TableHeader>
            <TableRow className="bg-[#FDFBF7] hover:bg-[#FDFBF7]">
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Mobile
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Message
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Status
              </TableHead>
              <TableHead className="text-[#721C24] font-semibold uppercase text-xs tracking-wider">
                Sent At
              </TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {pagedLogs.map((log) => (
              <TableRow
                key={log.id}
                data-testid={`whatsapp-log-${log.id}`}
                className="hover:bg-[#FFF9E6] transition-colors"
              >
                <TableCell className="font-medium">{log.mobile}</TableCell>
                <TableCell className="text-[#4A5568] max-w-md truncate">{log.message}</TableCell>
                <TableCell>
                  <div className="flex items-center gap-2">
                    {log.status === 'Delivered' ? (
                      <>
                        <CheckCircle size={16} className="text-green-600" />
                        <span className="text-sm text-green-600 font-medium">Delivered</span>
                      </>
                    ) : (
                      <>
                        <XCircle size={16} className="text-red-600" />
                        <span className="text-sm text-red-600 font-medium">Failed</span>
                      </>
                    )}
                  </div>
                </TableCell>
                <TableCell className="text-[#4A5568]">
                  {format(new Date(log.sent_at), 'MMM dd, yyyy HH:mm')}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
        <div className="flex items-center justify-between p-4 bg-white border-t border-slate-200">
          <div className="text-sm text-slate-500">
            Showing {Math.min((currentPage - 1) * rowsPerPage + 1, logs.length)} - {Math.min(currentPage * rowsPerPage, logs.length)} of {logs.length}
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

export default WhatsAppLogs;