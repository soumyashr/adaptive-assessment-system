// src/admin/pages/UploadData.jsx - WITH XLSX DOWNLOAD
import React, { useState } from 'react';
import { getThemeColors, DARK_MODE } from '../../config/theme';
import { Upload, FileText, Download, CheckCircle, AlertCircle, Info } from 'lucide-react';
import config from '../../config/config';
import notificationService from '../../services/notificationService';
import * as XLSX from 'xlsx';

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
  const colors = getThemeColors();

  const handleUpload = async () => {
    const sanitizedName = uploadConfig.name
      .toLowerCase()
      .trim()
      .replace(/\s+/g, '_')
      .replace(/[^a-z0-9_-]/g, '');

    if (!sanitizedName || sanitizedName.length < 3) {
      setError('Item bank name must be at least 3 characters');
      return;
    }

    if (!uploadConfig.displayName.trim()) {
      setError('Display name is required');
      return;
    }

    if (!uploadConfig.subject.trim()) {
      setError('Subject is required');
      return;
    }

    if (!selectedFile) {
      setError('Please select an Excel file');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const createResponse = await fetch(
        `${API_BASE}/item-banks/create?name=${encodeURIComponent(sanitizedName)}&display_name=${encodeURIComponent(uploadConfig.displayName)}&subject=${encodeURIComponent(uploadConfig.subject)}`,
        {
          method: 'POST',
          headers: { 'accept': 'application/json' }
        }
      );

      if (!createResponse.ok) {
        const errorData = await createResponse.json();
        throw new Error(errorData.detail || 'Failed to create item bank');
      }

      const formData = new FormData();
      formData.append('file', selectedFile);

      const uploadResponse = await fetch(
        `${API_BASE}/item-banks/${sanitizedName}/upload`,
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
        itemBank: sanitizedName
      });

      notificationService.success(`Success! Imported ${uploadData.imported} questions`);

      setUploadConfig({ name: '', displayName: '', subject: '' });
      setSelectedFile(null);

    } catch (err) {
      setError(err.message);
      notificationService.error(err.message);
    } finally {
      setLoading(false);
    }
  };

  const downloadTemplate = () => {
    // Create template data with required and optional columns
    const templateData = [
      {
        question: "What is 2 + 2?",
        option_a: "3",
        option_b: "4",
        option_c: "5",
        option_d: "6",
        answer: "B",
        tier: "C1",
        topic: "Arithmetic"
        // discrimination_a: "",
        // difficulty_b: "",
        // guessing_c: ""
      },
      {
        question: "Solve: x² = 16",
        option_a: "2",
        option_b: "4",
        option_c: "-4",
        option_d: "±4",
        answer: "D",
        tier: "C2",
        topic: "Algebra"
        // discrimination_a: "",
        // difficulty_b: "",
        // guessing_c: ""
      },
      {
        question: "What is the capital of France?",
        option_a: "London",
        option_b: "Paris",
        option_c: "Berlin",
        option_d: "Madrid",
        answer: "B",
        tier: "C1",
        topic: "Geography"
        // discrimination_a: "",
        // difficulty_b: "",
        // guessing_c: ""
      }
    ];

    // Create a new workbook
    const wb = XLSX.utils.book_new();

    // Convert data to worksheet
    const ws = XLSX.utils.json_to_sheet(templateData);

    // Set column widths for better readability
    ws['!cols'] = [
      { wch: 40 }, // question
      { wch: 15 }, // option_a
      { wch: 15 }, // option_b
      { wch: 15 }, // option_c
      { wch: 15 }, // option_d
      { wch: 10 }, // answer
      { wch: 10 }, // tier
      { wch: 15 }, // topic
      // { wch: 18 }, // discrimination_a
      // { wch: 15 }, // difficulty_b
      // { wch: 15 }  // guessing_c
    ];

    // Add worksheet to workbook
    XLSX.utils.book_append_sheet(wb, ws, "Item Bank Template");

    // Generate and download the file
    XLSX.writeFile(wb, 'item_bank_template.xlsx');

    notificationService.success('Excel template with 8 columns downloaded successfully!');
  };

  return (
    <div style={{ padding: '32px' }}>


        {/* Header */}
      <div
        className="mb-8 rounded-xl p-6"
        style={{
          backgroundColor: DARK_MODE ? '#292524' : '#ffffff',
          boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)'
        }}
      >
        <h1 className="text-3xl font-bold mb-2" style={{ color: colors.textPrimary }}>
          Upload Data
        </h1>
        <p style={{ color: colors.textMuted }}>
          Create new item banks and upload question sets
        </p>
      </div>

      {/* Success/Error Messages */}
      {result && (
        <div style={{
          marginBottom: '16px',
          padding: '12px 16px',
          background: colors.successBg,
          border: `1px solid ${colors.success}`,
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '13px'
        }}>
          <CheckCircle size={18} color={colors.success} />
          <div style={{ color: colors.success, fontWeight: '500' }}>
            {result.message}
          </div>
        </div>
      )}

      {error && (
        <div style={{
          marginBottom: '16px',
          padding: '12px 16px',
          background: colors.errorBg,
          border: `1px solid ${colors.error}`,
          borderRadius: '8px',
          display: 'flex',
          alignItems: 'center',
          gap: '10px',
          fontSize: '13px'
        }}>
          <AlertCircle size={18} color={colors.error} />
          <div style={{ color: colors.error, fontWeight: '500' }}>
            {error}
          </div>
        </div>
      )}

      {/* Main Grid - 3 Columns */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1.5fr 1fr 1fr',
        gap: '16px'
      }}>
        {/* Column 1: Configuration Form */}
        <div style={{
          background: colors.cardBg,
          border: `1px solid ${colors.cardBorder}`,
          borderRadius: '10px',
          padding: '20px'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '16px' }}>
            <div style={{
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: colors.primaryGradient,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <FileText size={20} color="white" />
            </div>
            <h2 style={{ fontSize: '16px', fontWeight: 'bold', color: colors.textPrimary, margin: 0 }}>
              Item Bank Configuration
            </h2>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            <div>
              <label style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: '600',
                marginBottom: '5px',
                color: colors.textPrimary
              }}>
                Item Bank Name <span style={{ color: colors.error }}>*</span>
              </label>
              <input
                type="text"
                placeholder="e.g., maths, vocabulary"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: `1px solid ${colors.inputBorder}`,
                  background: colors.inputBg,
                  color: colors.inputText,
                  fontSize: '13px',
                  outline: 'none'
                }}
                value={uploadConfig.name}
                onChange={(e) => setUploadConfig({...uploadConfig, name: e.target.value})}
                onFocus={(e) => e.target.style.borderColor = colors.primary}
                onBlur={(e) => e.target.style.borderColor = colors.inputBorder}
              />
              <p style={{ fontSize: '10px', marginTop: '3px', color: colors.textMuted }}>
                Lowercase, no spaces
              </p>
            </div>

            <div>
              <label style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: '600',
                marginBottom: '5px',
                color: colors.textPrimary
              }}>
                Display Name <span style={{ color: colors.error }}>*</span>
              </label>
              <input
                type="text"
                placeholder="e.g., Mathematics Assessment"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: `1px solid ${colors.inputBorder}`,
                  background: colors.inputBg,
                  color: colors.inputText,
                  fontSize: '13px',
                  outline: 'none'
                }}
                value={uploadConfig.displayName}
                onChange={(e) => setUploadConfig({...uploadConfig, displayName: e.target.value})}
                onFocus={(e) => e.target.style.borderColor = colors.primary}
                onBlur={(e) => e.target.style.borderColor = colors.inputBorder}
              />
            </div>

            <div>
              <label style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: '600',
                marginBottom: '5px',
                color: colors.textPrimary
              }}>
                Subject <span style={{ color: colors.error }}>*</span>
              </label>
              <input
                type="text"
                placeholder="e.g., Mathematics"
                style={{
                  width: '100%',
                  padding: '8px 12px',
                  borderRadius: '6px',
                  border: `1px solid ${colors.inputBorder}`,
                  background: colors.inputBg,
                  color: colors.inputText,
                  fontSize: '13px',
                  outline: 'none'
                }}
                value={uploadConfig.subject}
                onChange={(e) => setUploadConfig({...uploadConfig, subject: e.target.value})}
                onFocus={(e) => e.target.style.borderColor = colors.primary}
                onBlur={(e) => e.target.style.borderColor = colors.inputBorder}
              />
            </div>

            {/* File Upload */}
            <div>
              <label style={{
                display: 'block',
                fontSize: '12px',
                fontWeight: '600',
                marginBottom: '5px',
                color: colors.textPrimary
              }}>
                Excel File <span style={{ color: colors.error }}>*</span>
              </label>
              <div
                onClick={() => document.getElementById('file-upload').click()}
                style={{
                  border: `2px dashed ${selectedFile ? colors.success : colors.cardBorder}`,
                  borderRadius: '8px',
                  padding: '16px',
                  textAlign: 'center',
                  cursor: 'pointer',
                  background: selectedFile ? colors.successBg : colors.inputBg,
                  transition: 'all 0.2s'
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.borderColor = colors.primary;
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.borderColor = selectedFile ? colors.success : colors.cardBorder;
                }}
              >
                <input
                  id="file-upload"
                  type="file"
                  accept=".xlsx"
                  onChange={(e) => setSelectedFile(e.target.files[0])}
                  style={{ display: 'none' }}
                />
                {selectedFile ? (
                  <>
                    <FileText size={32} color={colors.success} style={{ margin: '0 auto 6px' }} />
                    <div style={{ fontWeight: '600', fontSize: '13px', color: colors.textPrimary, marginBottom: '3px' }}>
                      {selectedFile.name}
                    </div>
                    <div style={{ fontSize: '11px', color: colors.textMuted }}>
                      {(selectedFile.size / 1024).toFixed(2)} KB
                    </div>
                  </>
                ) : (
                  <>
                    <Upload size={32} color={colors.textMuted} style={{ margin: '0 auto 6px' }} />
                    <div style={{ fontWeight: '600', fontSize: '13px', color: colors.textPrimary, marginBottom: '3px' }}>
                      Click to upload
                    </div>
                    <div style={{ fontSize: '11px', color: colors.textMuted }}>
                      Excel (.xlsx) only
                    </div>
                  </>
                )}
              </div>
            </div>

            <button
              onClick={handleUpload}
              disabled={loading || !selectedFile || !uploadConfig.name || !uploadConfig.displayName || !uploadConfig.subject}
              style={{
                width: '100%',
                padding: '10px',
                borderRadius: '6px',
                border: 'none',
                background: loading ? colors.border : colors.primaryGradient,
                color: 'white',
                fontWeight: '600',
                fontSize: '13px',
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: (loading || !selectedFile || !uploadConfig.name || !uploadConfig.displayName || !uploadConfig.subject) ? 0.5 : 1,
                transition: 'all 0.2s'
              }}
            >
              {loading ? 'Uploading...' : 'Create & Upload'}
            </button>
          </div>
        </div>

        {/* Column 2: Required Fields */}
        <div style={{
          background: colors.cardBg,
          border: `1px solid ${colors.cardBorder}`,
          borderRadius: '10px',
          padding: '20px'
        }}>
          <div style={{ marginBottom: '12px' }}>
            <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: colors.textPrimary, marginBottom: '8px', display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Info size={16} color={colors.primary} />
              Required Columns (8)
            </h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '11px' }}>
              {['question', 'option_a', 'option_b', 'option_c', 'option_d', 'answer', 'tier', 'topic'].map((field, i) => (
                <div key={i} style={{
                  padding: '5px 8px',
                  background: DARK_MODE ? 'rgba(59, 130, 246, 0.15)' : '#EFF6FF',
                  borderRadius: '4px',
                  fontFamily: 'monospace',
                  fontWeight: '500',
                  color: colors.textPrimary,
                  fontSize: '10px'
                }}>
                  {field}
                </div>
              ))}
            </div>
          </div>

          <div style={{
            padding: '10px',
            background: DARK_MODE ? 'rgba(16, 185, 129, 0.1)' : '#D1FAE5',
            border: `1px solid ${colors.success}`,
            borderRadius: '6px',
            fontSize: '11px',
            color: colors.success,
            lineHeight: '1.4'
          }}>
            IRT parameters (discrimination, difficulty, guessing) are auto-generated based on tier!
          </div>
        </div>

        {/* Column 3: Template Download - COMPACT */}
        <div style={{
          background: colors.cardBg,
          border: `1px solid ${colors.cardBorder}`,
          borderRadius: '10px',
          padding: '20px'
        }}>
          <h3 style={{ fontSize: '14px', fontWeight: 'bold', color: colors.textPrimary, marginBottom: '10px', display: 'flex', alignItems: 'center', gap: '6px' }}>
            <Download size={16} color={colors.success} />
            Excel Template
          </h3>

          <div style={{
            padding: '12px',
            background: DARK_MODE ? '#1a1a1a' : '#F9FAFB',
            borderRadius: '6px',
            marginBottom: '12px',
            fontSize: '10px',
            fontFamily: 'monospace',
            color: colors.textSecondary,
            overflowX: 'auto'
          }}>
            <div style={{ whiteSpace: 'nowrap' }}>
              <div style={{ color: colors.primary, marginBottom: '6px' }}>question | option_a | ...</div>
              <div>What is 2+2? | 3 | 4 | ...</div>
              <div>Solve x²=16 | 2 | 4 | ...</div>
            </div>
          </div>

          <button
            onClick={downloadTemplate}
            style={{
              width: '100%',
              padding: '10px',
              borderRadius: '6px',
              border: `1px solid ${colors.success}`,
              background: colors.successBg,
              color: colors.success,
              fontWeight: '600',
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '6px',
              marginBottom: '12px'
            }}
          >
            <Download size={16} />
            Download XLSX
          </button>

          <div style={{
            padding: '10px',
            background: DARK_MODE ? 'rgba(16, 185, 129, 0.1)' : '#D1FAE5',
            border: `1px solid ${colors.success}`,
            borderRadius: '6px',
            fontSize: '11px',
            color: colors.success,
            lineHeight: '1.4'
          }}>
            Ready-to-use Excel template with sample data
          </div>
        </div>
      </div>
    </div>
  );
};

export default UploadData;