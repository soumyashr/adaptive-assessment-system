import React, { useState } from 'react';
import { theme } from '../../config/theme';
import config from '../../config/config';

const UploadData = () => {
  const [uploadConfig, setUploadConfig] = useState({
    name: '',
    displayName: '',
    subject: ''
  });
  const [selectedFile, setSelectedFile] = useState(null);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);

  const API_BASE = config.API_BASE_URL;

  const handleUpload = async () => {
    if (!selectedFile || !uploadConfig.name || !uploadConfig.displayName || !uploadConfig.subject) {
        setError('Please fill all required fields');
        return;
      }

      setLoading(true);
      setError(null);
      setResult(null);

      try {
        // Create item bank
        const createResponse = await fetch(
          `${API_BASE}/item-banks/create?name=${encodeURIComponent(uploadConfig.name)}&display_name=${encodeURIComponent(uploadConfig.displayName)}&subject=${encodeURIComponent(uploadConfig.subject)}`,
          {
            method: 'POST',
            headers: { 'accept': 'application/json' }
          }
        );

        if (!createResponse.ok) {
          const errorData = await createResponse.json();
          // ✅ FIX: Set error directly from detail, don't throw
          setError(errorData.detail || 'Failed to create item bank');
          setLoading(false);
          return; // Stop here, don't continue to upload
        }

        // Upload Excel file
        const formData = new FormData();
        formData.append('file', selectedFile);

        const uploadResponse = await fetch(
          `${API_BASE}/item-banks/${uploadConfig.name}/upload`,
          {
            method: 'POST',
            body: formData
          }
        );

        if (!uploadResponse.ok) {
          const errorData = await uploadResponse.json();
          // FIX: Set error directly from detail, don't throw
          setError(errorData.detail || 'Failed to upload questions');
          setLoading(false);
          return;
        }

        const uploadData = await uploadResponse.json();
        setResult({
          success: true,
          message: `Successfully imported ${uploadData.imported} questions`,
          itemBank: uploadConfig.name
        });

        // Reset form
        setUploadConfig({ name: '', displayName: '', subject: '' });
        setSelectedFile(null);

      } catch (err) {
        // FIX: This catch is now only for network errors
        setError('Network error. Please check your connection and try again.');
        console.error('Upload error:', err);
      } finally {
        setLoading(false);
      }
  };

  return (
    <div className={`p-8 ${theme('bg-gray-900', 'bg-gray-50')} min-h-screen`}>
      <h1 className={`text-3xl font-bold ${theme('text-white', 'text-gray-900')} mb-2`}>Upload Data</h1>
      <p className={`${theme('text-gray-400', 'text-gray-600')} mb-8`}>Create new item banks and upload question sets</p>

      {/* Success Message */}
      {result && (
        <div className={`${theme('bg-green-900/30 border-green-700 text-green-300', 'bg-green-50 border-green-200 text-green-800')} border px-6 py-4 rounded-lg mb-6`}>
          <div className="flex items-center gap-3">
            <span className="text-2xl">✓</span>
            <div>
              <div className="font-bold">{result.message}</div>
              <div className="text-sm">Item bank '{result.itemBank}' created successfully</div>
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {error && (
        <div className={`${theme('bg-red-900/30 border-red-700 text-red-300', 'bg-red-50 border-red-200 text-red-800')} border px-6 py-4 rounded-lg mb-6`}>
          <div className="flex items-center gap-3">
            <span className="text-2xl">✗</span>
            <div>{error}</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-8">
        {/* Upload Form */}
        <div className={`${theme('bg-gray-800 border-gray-700', 'bg-white')} rounded-lg shadow p-6 ${theme('border', '')}`}>
          <h2 className={`text-xl font-bold mb-6 ${theme('text-white', 'text-gray-900')}`}>Item Bank Configuration</h2>

          <div className="space-y-4">
            <div>
              <label className={`block text-sm font-medium ${theme('text-gray-300', 'text-gray-700')} mb-2`}>
                Item Bank Name*
              </label>
              <input
                type="text"
                placeholder="e.g., maths, vocabulary"
                className={`w-full ${theme('bg-gray-700 border-gray-600 text-white placeholder-gray-400', 'bg-white border-gray-300 text-gray-900 placeholder-gray-500')} border rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                value={uploadConfig.name}
                onChange={(e) => setUploadConfig({...uploadConfig, name: e.target.value})}
              />
              <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mt-1`}>
                Lowercase, no spaces (used in URLs)
              </p>
            </div>

            <div>
              <label className={`block text-sm font-medium ${theme('text-gray-300', 'text-gray-700')} mb-2`}>
                Display Name*
              </label>
              <input
                type="text"
                placeholder="e.g., Mathematics Assessment"
                className={`w-full ${theme('bg-gray-700 border-gray-600 text-white placeholder-gray-400', 'bg-white border-gray-300 text-gray-900 placeholder-gray-500')} border rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                value={uploadConfig.displayName}
                onChange={(e) => setUploadConfig({...uploadConfig, displayName: e.target.value})}
              />
              <p className={`text-xs ${theme('text-gray-400', 'text-gray-500')} mt-1`}>
                Friendly name shown to users
              </p>
            </div>

            <div>
              <label className={`block text-sm font-medium ${theme('text-gray-300', 'text-gray-700')} mb-2`}>
                Subject*
              </label>
              <input
                type="text"
                placeholder="e.g., Mathematics"
                className={`w-full ${theme('bg-gray-700 border-gray-600 text-white placeholder-gray-400', 'bg-white border-gray-300 text-gray-900 placeholder-gray-500')} border rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent`}
                value={uploadConfig.subject}
                onChange={(e) => setUploadConfig({...uploadConfig, subject: e.target.value})}
              />
            </div>

            <div>
                <label className={`block text-sm font-medium ${theme('text-gray-300', 'text-gray-700')} mb-2`}>
                  Questions Excel File*
                </label>
                <div className={`border-2 border-dashed ${theme('border-gray-600 hover:border-blue-500', 'border-gray-300 hover:border-blue-500')} rounded-lg p-6 text-center transition`}>
                  <input
                    type="file"
                    accept=".xlsx"
                    onChange={(e) => setSelectedFile(e.target.files[0])}
                    className="hidden"
                    id="file-upload"
                  />
                  <label htmlFor="file-upload" className="cursor-pointer">
                    {selectedFile ? (
                      <div>
                        <div className="text-4xl mb-2">📄</div>
                        <div className={`font-medium ${theme('text-gray-200', 'text-gray-900')}`}>{selectedFile.name}</div>
                        <div className={`text-sm ${theme('text-gray-400', 'text-gray-500')}`}>{(selectedFile.size / 1024).toFixed(2)} KB</div>
                      </div>
                    ) : (
                      <div>
                        <div className="text-4xl mb-2">📤</div>
                        <div className={`font-medium ${theme('text-gray-200', 'text-gray-900')}`}>Click to upload</div>
                        <div className={`text-sm ${theme('text-gray-400', 'text-gray-500')}`}>Excel (.xlsx) files only</div>
                      </div>
                    )}
                  </label>
                </div>


            </div>

            <button
              onClick={handleUpload}
              disabled={loading || !selectedFile || !uploadConfig.name}
              className="w-full bg-blue-500 hover:bg-blue-600 text-white py-3 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Uploading...' : 'Create & Upload'}
            </button>
          </div>
        </div>

        {/* Instructions */}
        <div className={`${theme('bg-blue-900/30 border-blue-700', 'bg-blue-50')} rounded-lg p-6 ${theme('border', '')}`}>
          <h3 className={`text-lg font-bold ${theme('text-blue-300', 'text-blue-900')} mb-4`}>📋 Excel File Format Requirements</h3>


          <div className="space-y-4 text-sm">
            <div>
              <div className={`font-medium ${theme('text-blue-200', 'text-blue-900')} mb-2`}>Required Columns:</div>
              <ul className={`list-disc list-inside space-y-1 ${theme('text-blue-300', 'text-blue-800')}`}>
                <li><code className={`${theme('bg-blue-800/50', 'bg-blue-100')} px-2 py-1 rounded`}>question</code> - Question text</li>
                <li><code className={`${theme('bg-blue-800/50', 'bg-blue-100')} px-2 py-1 rounded`}>option_a</code> - First option</li>
                <li><code className={`${theme('bg-blue-800/50', 'bg-blue-100')} px-2 py-1 rounded`}>option_b</code> - Second option</li>
                <li><code className={`${theme('bg-blue-800/50', 'bg-blue-100')} px-2 py-1 rounded`}>option_c</code> - Third option</li>
                <li><code className={`${theme('bg-blue-800/50', 'bg-blue-100')} px-2 py-1 rounded`}>option_d</code> - Fourth option</li>
                <li><code className={`${theme('bg-blue-800/50', 'bg-blue-100')} px-2 py-1 rounded`}>answer</code> - Correct answer (A/B/C/D)</li>
                <li><code className={`${theme('bg-blue-800/50', 'bg-blue-100')} px-2 py-1 rounded`}>tier</code> - Difficulty tier (C1/C2/C3/C4)</li>
                <li><code className={`${theme('bg-blue-800/50', 'bg-blue-100')} px-2 py-1 rounded`}>topic</code> - Question topic</li>
              </ul>
            </div>

            <div>
              <div className={`font-medium ${theme('text-blue-200', 'text-blue-900')} mb-2`}>Optional Columns:</div>
              <ul className={`list-disc list-inside space-y-1 ${theme('text-blue-300', 'text-blue-800')}`}>
                <li><code className={`${theme('bg-blue-800/50', 'bg-blue-100')} px-2 py-1 rounded`}>discrimination_a</code> - Default: 1.5</li>
                <li><code className={`${theme('bg-blue-800/50', 'bg-blue-100')} px-2 py-1 rounded`}>difficulty_b</code> - Auto-assigned by tier</li>
                <li><code className={`${theme('bg-blue-800/50', 'bg-blue-100')} px-2 py-1 rounded`}>guessing_c</code> - Default: 0.25</li>
              </ul>
            </div>

            <div className={`${theme('bg-blue-800/30 border-blue-700', 'bg-blue-100 border-blue-200')} border p-4 rounded-lg`}>
              <div className={`font-medium ${theme('text-blue-200', 'text-blue-900')} mb-2`}>💡 Example Structure:</div>
                <div className={`text-xs ${theme('text-blue-300', 'text-blue-800')}`}>
                  <p className="mb-2">Create an Excel file (.xlsx) with these columns in the first row:</p>
                  <pre className="overflow-x-auto">
                {`question | option_a | option_b | option_c | option_d | answer | tier | topic
                What is 2+2? | 3 | 4 | 5 | 6 | B | C1 | Arithmetic
                Solve: x² = 16 | 2 | 4 | -4 | ±4 | D | C2 | Algebra`}
                  </pre>
                </div>


            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadData;