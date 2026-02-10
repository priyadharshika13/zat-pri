import React, { useState, useEffect, FormEvent } from 'react';
import { Card } from '../components/common/Card';
import { Button } from '../components/common/Button';
import { Badge } from '../components/common/Badge';
import { Loader } from '../components/common/Loader';
import { useLanguage } from '../context/LanguageContext';
import { getZatcaStatus, generateCsr, uploadCsid, ZatcaStatus, CsrGenerateRequest } from '../lib/zatcaApi';

export const ZatcaSetup: React.FC = () => {
  const { direction, t } = useLanguage();
  
  // State
  const [status, setStatus] = useState<ZatcaStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [environment, setEnvironment] = useState<'SANDBOX' | 'PRODUCTION'>('SANDBOX');
  
  // CSR Generation state
  const [generatingCsr, setGeneratingCsr] = useState(false);
  const [csrData, setCsrData] = useState<{ csr: string; privateKey: string } | null>(null);
  const [csrFormData, setCsrFormData] = useState({
    common_name: '',
    organization: '',
    organizational_unit: '',
    country: 'SA',
    state: '',
    locality: '',
    email: '',
  });
  
  // CSID Upload state
  const [uploading, setUploading] = useState(false);
  const [certificateFile, setCertificateFile] = useState<File | null>(null);
  const [privateKeyFile, setPrivateKeyFile] = useState<File | null>(null);
  
  // Load status on mount and when environment changes
  useEffect(() => {
    loadStatus();
  }, [environment]);
  
  const loadStatus = async () => {
    try {
      setLoading(true);
      setError(null);
      const statusData = await getZatcaStatus(environment);
      setStatus(statusData);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to load ZATCA status';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };
  
  const handleGenerateCsr = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setError(null);
    setGeneratingCsr(true);
    
    try {
      const request: CsrGenerateRequest = {
        environment,
        common_name: csrFormData.common_name,
        organization: csrFormData.organization || undefined,
        organizational_unit: csrFormData.organizational_unit || undefined,
        country: csrFormData.country || undefined,
        state: csrFormData.state || undefined,
        locality: csrFormData.locality || undefined,
        email: csrFormData.email || undefined,
      };
      
      const response = await generateCsr(request);
      setCsrData({
        csr: response.csr,
        privateKey: response.private_key,
      });
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to generate CSR';
      setError(errorMessage);
    } finally {
      setGeneratingCsr(false);
    }
  };
  
  const downloadFile = (content: string, filename: string, contentType: string = 'text/plain') => {
    const blob = new Blob([content], { type: contentType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };
  
  const handleDownloadCsr = () => {
    if (csrData) {
      downloadFile(csrData.csr, 'zatca-csr.pem', 'application/x-pem-file');
    }
  };
  
  const handleDownloadPrivateKey = () => {
    if (csrData) {
      downloadFile(csrData.privateKey, 'zatca-private-key.pem', 'application/x-pem-file');
    }
  };
  
  const handleUploadCsid = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    
    if (!certificateFile || !privateKeyFile) {
      setError('Please select both certificate and private key files');
      return;
    }
    
    setError(null);
    setUploading(true);
    
    try {
      await uploadCsid(environment, certificateFile, privateKeyFile);
      // Reload status after successful upload
      await loadStatus();
      // Reset form
      setCertificateFile(null);
      setPrivateKeyFile(null);
      // Reset file inputs
      const certInput = document.getElementById('certificate-file') as HTMLInputElement;
      const keyInput = document.getElementById('private-key-file') as HTMLInputElement;
      if (certInput) certInput.value = '';
      if (keyInput) keyInput.value = '';
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to upload CSID';
      setError(errorMessage);
    } finally {
      setUploading(false);
    }
  };
  
  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A';
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };
  
  if (loading && !status) {
    return (
      <div className="min-h-screen bg-slate-50 flex items-center justify-center" dir={direction}>
        <Loader size="lg" />
      </div>
    );
  }
  
  return (
    <div className="space-y-6" dir={direction} data-testid="zatca-setup-page">
      {/* Page Title */}
      <div>
        <h1 className="text-2xl font-bold text-slate-900">ZATCA Setup</h1>
        <p className="text-slate-500 mt-1">
          Manage your ZATCA connection and certificates
        </p>
      </div>
      
      {/* Error Banner */}
      {error && (
        <Card padding="md" className="bg-red-50 border-red-200">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            <p className="text-red-800">{error}</p>
          </div>
        </Card>
      )}
      
      {/* Status Card */}
      <Card padding="md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Connection Status</h2>
          <div className="flex items-center gap-3">
            <label className="text-sm text-slate-600">Environment:</label>
            <select
              value={environment}
              onChange={(e) => setEnvironment(e.target.value as 'SANDBOX' | 'PRODUCTION')}
              className="px-3 py-1.5 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500"
            >
              <option value="SANDBOX">Sandbox</option>
              <option value="PRODUCTION">Production</option>
            </select>
            <Button
              variant="outline"
              size="sm"
              onClick={loadStatus}
              isLoading={loading}
            >
              Refresh
            </Button>
          </div>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-medium text-slate-700">Status:</span>
              {status?.connected ? (
                <Badge variant="success">Connected</Badge>
              ) : (
                <Badge variant="danger">Disconnected</Badge>
              )}
            </div>
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-medium text-slate-700">Environment:</span>
              <Badge variant={status?.environment === 'PRODUCTION' ? 'warning' : 'info'}>
                {status?.environment === 'PRODUCTION' ? 'Production' : 'Sandbox'}
              </Badge>
            </div>
          </div>
          
          <div>
            {status?.certificate && (
              <>
                <div className="mb-2">
                  <span className="text-sm font-medium text-slate-700">Certificate Expiry:</span>
                  <span className="text-sm text-slate-600 ms-2">
                    {formatDate(status.certificate_expiry)}
                  </span>
                </div>
                <div>
                  <span className="text-sm font-medium text-slate-700">Last Sync:</span>
                  <span className="text-sm text-slate-600 ms-2">
                    {formatDate(status.last_sync)}
                  </span>
                </div>
              </>
            )}
            {!status?.certificate && (
              <p className="text-sm text-slate-500">No certificate uploaded</p>
            )}
          </div>
        </div>
      </Card>
      
      {/* Generate CSR Section */}
      <Card padding="md">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Generate Certificate Signing Request (CSR)</h2>
        <p className="text-sm text-slate-600 mb-4">
          Generate a CSR to request a CSID certificate from ZATCA. You'll need to download both the CSR and private key.
        </p>
        
        {!csrData ? (
          <form onSubmit={handleGenerateCsr} className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Common Name (CN) <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  required
                  value={csrFormData.common_name}
                  onChange={(e) => setCsrFormData({ ...csrFormData, common_name: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="e.g., company-name.com"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Organization (O)
                </label>
                <input
                  type="text"
                  value={csrFormData.organization}
                  onChange={(e) => setCsrFormData({ ...csrFormData, organization: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="Company Name"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Organizational Unit (OU)
                </label>
                <input
                  type="text"
                  value={csrFormData.organizational_unit}
                  onChange={(e) => setCsrFormData({ ...csrFormData, organizational_unit: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="Department"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Country (C)
                </label>
                <input
                  type="text"
                  value={csrFormData.country}
                  onChange={(e) => setCsrFormData({ ...csrFormData, country: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="SA"
                  maxLength={2}
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  State/Province (ST)
                </label>
                <input
                  type="text"
                  value={csrFormData.state}
                  onChange={(e) => setCsrFormData({ ...csrFormData, state: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="Riyadh"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Locality/City (L)
                </label>
                <input
                  type="text"
                  value={csrFormData.locality}
                  onChange={(e) => setCsrFormData({ ...csrFormData, locality: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="Riyadh"
                />
              </div>
              
              <div className="md:col-span-2">
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Email Address
                </label>
                <input
                  type="email"
                  value={csrFormData.email}
                  onChange={(e) => setCsrFormData({ ...csrFormData, email: e.target.value })}
                  className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
                  placeholder="admin@company.com"
                />
              </div>
            </div>
            
            <div className="flex justify-end">
              <Button type="submit" isLoading={generatingCsr}>
                Generate CSR
              </Button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="bg-green-50 border border-green-200 rounded-lg p-4">
              <p className="text-sm text-green-800 mb-3">
                CSR generated successfully! Please download both files and save the private key securely.
              </p>
              <div className="flex gap-2">
                <Button variant="outline" size="sm" onClick={handleDownloadCsr}>
                  Download CSR
                </Button>
                <Button variant="outline" size="sm" onClick={handleDownloadPrivateKey}>
                  Download Private Key
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => {
                    setCsrData(null);
                    setCsrFormData({
                      common_name: '',
                      organization: '',
                      organizational_unit: '',
                      country: 'SA',
                      state: '',
                      locality: '',
                      email: '',
                    });
                  }}
                >
                  Generate New CSR
                </Button>
              </div>
            </div>
          </div>
        )}
      </Card>
      
      {/* Upload CSID Section */}
      <Card padding="md">
        <h2 className="text-lg font-semibold text-slate-900 mb-4">Upload CSID Certificate</h2>
        <p className="text-sm text-slate-600 mb-4">
          Upload your CSID certificate and private key obtained from ZATCA after submitting the CSR.
        </p>
        
        <form onSubmit={handleUploadCsid} className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Certificate File (.pem, .crt, .cer) <span className="text-red-500">*</span>
              </label>
              <input
                id="certificate-file"
                type="file"
                required
                accept=".pem,.crt,.cer"
                onChange={(e) => setCertificateFile(e.target.files?.[0] || null)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
            
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Private Key File (.pem, .key) <span className="text-red-500">*</span>
              </label>
              <input
                id="private-key-file"
                type="file"
                required
                accept=".pem,.key"
                onChange={(e) => setPrivateKeyFile(e.target.files?.[0] || null)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-emerald-500"
              />
            </div>
          </div>
          
          <div className="flex justify-end">
            <Button type="submit" isLoading={uploading}>
              Upload CSID
            </Button>
          </div>
        </form>
      </Card>
    </div>
  );
};

