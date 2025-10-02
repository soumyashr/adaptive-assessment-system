import React, { useState } from 'react';

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

  const API_BASE = 'http://localhost:8000/api';

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
        throw new Error(errorData.detail || 'Failed to create item bank');
      }

      // Upload CSV
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
        throw new Error(errorData.detail || 'Failed to upload questions');
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
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-8">
      <h1 className="text-3xl font-bold text-gray-900 mb-2">Upload Data</h1>
      <p className="text-gray-600 mb-8">Create new item banks and upload question sets</p>

      {/* Success Message */}
      {result && (
        <div className="bg-green-50 border border-green-200 text-green-800 px-6 py-4 rounded-lg mb-6">
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
        <div className="bg-red-50 border border-red-200 text-red-800 px-6 py-4 rounded-lg mb-6">
          <div className="flex items-center gap-3">
            <span className="text-2xl">✗</span>
            <div>{error}</div>
          </div>
        </div>
      )}

      <div className="grid grid-cols-2 gap-8">
        {/* Upload Form */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-bold mb-6">Item Bank Configuration</h2>

          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Item Bank Name*
              </label>
              <input
                type="text"
                placeholder="e.g., maths, vocabulary"
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={uploadConfig.name}
                onChange={(e) => setUploadConfig({...uploadConfig, name: e.target.value})}
              />
              <p className="text-xs text-gray-500 mt-1">
                Lowercase, no spaces (used in URLs)
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Display Name*
              </label>
              <input
                type="text"
                placeholder="e.g., Mathematics Assessment"
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={uploadConfig.displayName}
                onChange={(e) => setUploadConfig({...uploadConfig, displayName: e.target.value})}
              />
              <p className="text-xs text-gray-500 mt-1">
                Friendly name shown to users
              </p>
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Subject*
              </label>
              <input
                type="text"
                placeholder="e.g., Mathematics"
                className="w-full border border-gray-300 rounded-lg px-4 py-3 focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                value={uploadConfig.subject}
                onChange={(e) => setUploadConfig({...uploadConfig, subject: e.target.value})}
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Questions CSV File*
              </label>
              <div className="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 transition">
                <input
                  type="file"
                  accept=".csv"
                  onChange={(e) => setSelectedFile(e.target.files[0])}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  {selectedFile ? (
                    <div>
                      <div className="text-4xl mb-2">📄</div>
                      <div className="font-medium text-gray-900">{selectedFile.name}</div>
                      <div className="text-sm text-gray-500">{(selectedFile.size / 1024).toFixed(2)} KB</div>
                    </div>
                  ) : (
                    <div>
                      <div className="text-4xl mb-2">📤</div>
                      <div className="font-medium text-gray-900">Click to upload</div>
                      <div className="text-sm text-gray-500">CSV files only</div>
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
        <div className="bg-blue-50 rounded-lg p-6">
          <h3 className="text-lg font-bold text-blue-900 mb-4">📋 CSV Format Requirements</h3>

          <div className="space-y-4 text-sm">
            <div>
              <div className="font-medium text-blue-900 mb-2">Required Columns:</div>
              <ul className="list-disc list-inside space-y-1 text-blue-800">
                <li><code className="bg-blue-100 px-2 py-1 rounded">question</code> - Question text</li>
                <li><code className="bg-blue-100 px-2 py-1 rounded">option_a</code> - First option</li>
                <li><code className="bg-blue-100 px-2 py-1 rounded">option_b</code> - Second option</li>
                <li><code className="bg-blue-100 px-2 py-1 rounded">option_c</code> - Third option</li>
                <li><code className="bg-blue-100 px-2 py-1 rounded">option_d</code> - Fourth option</li>
                <li><code className="bg-blue-100 px-2 py-1 rounded">answer</code> - Correct answer (A/B/C/D)</li>
                <li><code className="bg-blue-100 px-2 py-1 rounded">tier</code> - Difficulty tier (C1/C2/C3/C4)</li>
                <li><code className="bg-blue-100 px-2 py-1 rounded">topic</code> - Question topic</li>
              </ul>
            </div>

            <div>
              <div className="font-medium text-blue-900 mb-2">Optional Columns:</div>
              <ul className="list-disc list-inside space-y-1 text-blue-800">
                <li><code className="bg-blue-100 px-2 py-1 rounded">discrimination_a</code> - Default: 1.5</li>
                <li><code className="bg-blue-100 px-2 py-1 rounded">difficulty_b</code> - Auto-assigned by tier</li>
                <li><code className="bg-blue-100 px-2 py-1 rounded">guessing_c</code> - Default: 0.25</li>
              </ul>
            </div>

            <div className="bg-blue-100 p-4 rounded-lg">
              <div className="font-medium text-blue-900 mb-2">💡 Example CSV:</div>
              <pre className="text-xs text-blue-800 overflow-x-auto">
{`question,option_a,option_b,option_c,option_d,answer,tier,topic
"What is 2+2?",3,4,5,6,B,C1,Arithmetic
"Solve: x² = 16",2,4,-4,"±4",D,C2,Algebra`}
              </pre>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadData;