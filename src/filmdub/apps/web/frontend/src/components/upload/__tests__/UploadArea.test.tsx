/** UploadArea 组件测试 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { UploadArea } from '../UploadArea';

describe('UploadArea', () => {
  it('应该渲染上传区域', () => {
    render(<UploadArea mediaType="video" />);
    expect(screen.getByText(/拖拽文件到此处/i)).toBeInTheDocument();
  });

  it('应该显示文件大小限制', () => {
    render(<UploadArea mediaType="video" maxFileSize={1024 * 1024} />);
    expect(screen.getByText(/1 MB/i)).toBeInTheDocument();
  });

  it('应该支持选择的媒体类型', () => {
    render(<UploadArea mediaType="audio" />);
    expect(screen.getByText(/音频/i)).toBeInTheDocument();
  });

  it('应该在上传开始时调用 onUploadStart', async () => {
    const onUploadStart = vi.fn();
    render(<UploadArea mediaType="video" onUploadStart={onUploadStart} />);

    const input = screen.getByRole('textbox', { hidden: true });
    const file = new File(['content'], 'test.mp4', { type: 'video/mp4' });

    await userEvent.upload(input, file);

    await waitFor(() => {
      expect(onUploadStart).toHaveBeenCalledWith(file);
    });
  });

  it('应该禁用上传区域', () => {
    render(<UploadArea mediaType="video" disabled />);
    const dropzone = screen.getByText(/拖拽文件到此处/i).parentElement;
    expect(dropzone).toHaveClass('opacity-50', 'cursor-not-allowed');
  });

  it('应该显示文件类型错误', async () => {
    render(<UploadArea mediaType="video" />);

    const input = screen.getByRole('textbox', { hidden: true });
    const file = new File(['content'], 'test.exe', { type: 'application/octet-stream' });

    await userEvent.upload(input, file);

    await waitFor(() => {
      expect(screen.getByText(/不支持的文件类型/i)).toBeInTheDocument();
    });
  });
});
