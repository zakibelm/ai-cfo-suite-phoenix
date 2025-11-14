/**
 * Tests for API Service
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';
import { checkBackendHealth, sendQuery } from './apiService';

describe('apiService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('checkBackendHealth', () => {
    it('should return true when backend is healthy', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => ({ status: 'healthy' }),
      } as Response);

      const result = await checkBackendHealth();

      expect(result).toBe(true);
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/monitoring/health')
      );
    });

    it('should return false when backend is unhealthy', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
      } as Response);

      const result = await checkBackendHealth();

      expect(result).toBe(false);
    });

    it('should return false when fetch throws error', async () => {
      global.fetch = vi.fn().mockRejectedValueOnce(new Error('Network error'));

      const result = await checkBackendHealth();

      expect(result).toBe(false);
    });
  });

  describe('sendQuery', () => {
    it('should send query successfully', async () => {
      const mockResponse = {
        agent: 'TestAgent',
        response: 'Test response',
        sources: [],
        processing_time: 100,
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await sendQuery('test query', null);

      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/query'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Content-Type': 'application/json',
          }),
          body: expect.stringContaining('test query'),
        })
      );
    });

    it('should include document context when provided', async () => {
      const mockDocument = {
        id: 'doc1',
        name: 'test.pdf',
        status: 'Processed' as const,
        uploaded: new Date().toISOString(),
        doctype: 'Financial',
        country: 'CA',
        size_bytes: 1000,
        sha256: 'abc123',
      };

      const mockResponse = {
        agent: 'TestAgent',
        response: 'Test response with context',
        sources: [{ document: 'test.pdf' }],
        processing_time: 150,
      };

      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      } as Response);

      const result = await sendQuery('test query', mockDocument);

      expect(result).toEqual(mockResponse);
      expect(fetch).toHaveBeenCalledWith(
        expect.anything(),
        expect.objectContaining({
          body: expect.stringContaining('test.pdf'),
        })
      );
    });

    it('should throw error when request fails', async () => {
      global.fetch = vi.fn().mockResolvedValueOnce({
        ok: false,
        statusText: 'Internal Server Error',
      } as Response);

      await expect(sendQuery('test query', null)).rejects.toThrow(
        'Failed to send query'
      );
    });

    it('should handle network errors', async () => {
      global.fetch = vi.fn().mockRejectedValueOnce(new Error('Network error'));

      await expect(sendQuery('test query', null)).rejects.toThrow();
    });
  });
});
