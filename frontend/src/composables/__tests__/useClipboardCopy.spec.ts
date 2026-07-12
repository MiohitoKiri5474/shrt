import { describe, it, expect, vi, afterEach } from 'vitest'
import { useClipboardCopy } from '../useClipboardCopy'

describe('useClipboardCopy', () => {
  afterEach(() => {
    vi.useRealTimers()
    // @ts-expect-error jsdom does not define navigator.clipboard by default
    delete navigator.clipboard
    // @ts-expect-error jsdom does not implement execCommand by default
    delete document.execCommand
    vi.restoreAllMocks()
  })

  it('calls the clipboard API when available and sets copied', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const { copied, copyError, copy } = useClipboardCopy()

    await copy('hello')

    expect(writeText).toHaveBeenCalledWith('hello')
    expect(copied.value).toBe(true)
    expect(copyError.value).toBe(false)
  })

  it('resets copied back to false after the timeout', async () => {
    vi.useFakeTimers()
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const { copied, copy } = useClipboardCopy()

    await copy('hello')
    expect(copied.value).toBe(true)

    await vi.advanceTimersByTimeAsync(1500)
    expect(copied.value).toBe(false)
  })

  it('sets copyError when the clipboard API rejects', async () => {
    const writeText = vi.fn().mockRejectedValue(new Error('denied'))
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    const { copied, copyError, copy } = useClipboardCopy()

    await copy('hello')

    expect(copied.value).toBe(false)
    expect(copyError.value).toBe(true)
  })

  it('falls back to execCommand when the Clipboard API is unavailable', async () => {
    const execCommand = vi.fn().mockReturnValue(true)
    document.execCommand = execCommand
    const { copied, copyError, copy } = useClipboardCopy()

    await copy('hello')

    expect(execCommand).toHaveBeenCalledWith('copy')
    expect(copied.value).toBe(true)
    expect(copyError.value).toBe(false)
  })

  it('treats a false execCommand return value as a failure without throwing', async () => {
    const execCommand = vi.fn().mockReturnValue(false)
    document.execCommand = execCommand
    const { copied, copyError, copy } = useClipboardCopy()

    await copy('hello')

    expect(execCommand).toHaveBeenCalledWith('copy')
    expect(copied.value).toBe(false)
    expect(copyError.value).toBe(true)
  })

  it('clears a previous copyError on the next successful copy attempt', async () => {
    const execCommand = vi.fn().mockReturnValue(false)
    document.execCommand = execCommand
    const { copied, copyError, copy } = useClipboardCopy()
    await copy('hello')
    expect(copyError.value).toBe(true)

    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', { value: { writeText }, configurable: true })
    await copy('hello again')

    expect(copyError.value).toBe(false)
    expect(copied.value).toBe(true)
  })
})
