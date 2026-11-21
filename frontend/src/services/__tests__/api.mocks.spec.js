import { afterEach, describe, expect, it, vi } from 'vitest'

async function loadMockedApi(env = {}) {
  vi.resetModules()
  vi.stubEnv('VITE_USE_MOCKS', 'true')
  for (const [key, value] of Object.entries(env)) {
    vi.stubEnv(key, String(value))
  }
  return import('../api.js')
}

afterEach(() => {
  vi.unstubAllEnvs()
  vi.resetModules()
})

describe('review API mocks', () => {
  it('builds a 100-block structure for large-document testing', async () => {
    const { getStructure } = await loadMockedApi({
      VITE_MOCK_REVIEW_LARGE: 'true',
      VITE_MOCK_REVIEW_BLOCKS: 100
    })

    const structure = await getStructure(1)

    expect(structure.status).toBe('review')
    expect(structure.original.blocks).toHaveLength(100)
    expect(structure.proposed.blocks).toHaveLength(100)
    expect(structure.summary.revertible_blocks.length).toBeGreaterThan(0)
    expect(structure.summary.chunks_fallback).toBeGreaterThan(0)
  })

  it('validates the accept/reject contract used by the review screen', async () => {
    const { submitReview } = await loadMockedApi()

    const accepted = await submitReview(1, { action: 'accept', revert: ['b1', 'b2'] })
    expect(accepted.document_id).toBe(1)
    expect(accepted.action).toBe('accept')
    expect(accepted.summary.reverted_blocks_count).toBe(2)

    const rejected = await submitReview(1, { action: 'reject' })
    expect(rejected.action).toBe('reject')
    expect(rejected.summary.reverted_blocks_count).toBe(0)

    await expect(submitReview(1, { action: 'unknown' })).rejects.toMatchObject({
      code: 'INVALID_CONFIG'
    })
  })
})
