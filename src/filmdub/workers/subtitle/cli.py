"""
Module 03 CLI 命令
"""

import click
import json
import logging
from pathlib import Path

from .runner import SubtitleRunner
from .config import SubtitleConfig, TranslationMode

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@click.group()
def subtitle():
    """字幕与对话获取命令"""
    pass


@subtitle.command()
@click.argument('project_id')
@click.option('--video-path', type=click.Path(exists=True), help='视频文件路径')
@click.option('--subtitle-en', type=click.Path(exists=True), help='外挂英文字幕文件（srt/ass等）')
@click.option('--subtitle-zh', type=click.Path(exists=True), help='外挂中文字幕文件，双语文件自动拆分')
@click.option('--subtitle-path', 'subtitle_paths', type=click.Path(exists=True), multiple=True,
              help='外挂字幕文件，按文件名自动识别语言（可多次指定）')
def start(project_id, video_path, subtitle_en, subtitle_zh, subtitle_paths):
    """
    开始字幕处理

    PROJECT_ID: 项目ID
    """
    click.echo(f"Starting subtitle processing for project: {project_id}")

    # 检查项目是否存在
    project_dir = Path(f"data/projects/{project_id}")
    if not project_dir.exists():
        click.echo(f"Error: Project {project_id} not found", err=True)
        return

    # 获取视频路径
    if not video_path:
        # 尝试从项目中查找视频
        video_path = project_dir / "media" / "source.mkv"
        if not video_path.exists():
            click.echo("Error: No video file found. Please specify --video-path", err=True)
            return

    # 创建工作器
    config = SubtitleConfig()
    runner = SubtitleRunner(project_id, config)

    # 执行
    result = runner.run(
        Path(video_path),
        subtitle_en=Path(subtitle_en) if subtitle_en else None,
        subtitle_zh=Path(subtitle_zh) if subtitle_zh else None,
        subtitle_auto=[Path(p) for p in subtitle_paths],
    )

    # 显示结果
    if result['status'] == 'success':
        click.echo("✅ Subtitle processing completed successfully!")
        click.echo(f"   Duration: {result['duration']:.2f}s")
        click.echo(f"   Steps completed: {len(result['steps'])}")
    else:
        click.echo(f"❌ Subtitle processing failed: {result.get('error')}", err=True)


@subtitle.command()
@click.argument('project_id')
def status(project_id):
    """
    查看字幕处理状态

    PROJECT_ID: 项目ID
    """
    project_dir = Path(f"data/projects/{project_id}")
    manifest_path = project_dir / "dialogue" / "dialogue_manifest.json"

    if not manifest_path.exists():
        click.echo(f"No dialogue manifest found for project {project_id}")
        return

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    click.echo(f"\n{'='*50}")
    click.echo(f"Dialogue Manifest - {project_id}")
    click.echo(f"{'='*50}\n")

    # 基本信息
    click.echo(f"Generated: {manifest.get('generated_at')}")
    click.echo(f"Translation Mode: {manifest.get('translation_mode')}")

    # 字幕来源
    click.echo(f"\nSubtitle Sources:")
    for source in manifest.get('subtitle_sources', []):
        click.echo(f"  - {source['language']}: {source.get('format', 'N/A')} ({source['source_type']})")

    # 验证
    validation = manifest.get('validation', {})
    if validation:
        click.echo(f"\nValidation:")
        click.echo(f"  Total: {validation.get('total_entries', 0)}")
        click.echo(f"  Valid: {validation.get('valid_entries', 0)}")
        click.echo(f"  Errors: {validation.get('error_count', 0)}")
        click.echo(f"  Warnings: {validation.get('warning_count', 0)}")
        click.echo(f"  Quality Score: {validation.get('quality_score', 0):.2f}")

    # 对齐
    alignment = manifest.get('alignment', {})
    if alignment:
        click.echo(f"\nAlignment:")
        click.echo(f"  Method: {alignment.get('method', 'N/A')}")
        click.echo(f"  Offset: {alignment.get('offset', 0):.2f}s")
        click.echo(f"  Scale: {alignment.get('scale', 1):.4f}")
        click.echo(f"  Confidence: {alignment.get('confidence', 0):.2f}")

    # 翻译
    translation = manifest.get('translation', {})
    if translation:
        click.echo(f"\nTranslation:")
        click.echo(f"  Source: {translation.get('source_language')}")
        click.echo(f"  Target: {translation.get('target_language')}")
        click.echo(f"  Translated: {translation.get('translated_count', 0)}")
        click.echo(f"  Untranslated: {translation.get('untranslated_count', 0)}")

    # 步骤
    click.echo(f"\nSteps:")
    for step in manifest.get('steps', []):
        status_icon = "✅" if step['status'] == 'success' else "❌"
        click.echo(f"  {status_icon} {step['step']}: {step['status']} ({step['duration']:.2f}s)")

    click.echo(f"\n{'='*50}\n")


@subtitle.command()
@click.argument('project_id')
def manifest(project_id):
    """
    显示对话清单

    PROJECT_ID: 项目ID
    """
    project_dir = Path(f"data/projects/{project_id}")
    manifest_path = project_dir / "dialogue" / "dialogue_manifest.json"

    if not manifest_path.exists():
        click.echo(f"No dialogue manifest found for project {project_id}")
        return

    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest = json.load(f)

    click.echo(json.dumps(manifest, indent=2, ensure_ascii=False))


@subtitle.command()
@click.argument('project_id')
@click.option('--limit', default=20, help='显示的对话数量')
def dialogues(project_id, limit):
    """
    查看对话列表

    PROJECT_ID: 项目ID
    """
    project_dir = Path(f"data/projects/{project_id}")
    jsonl_path = project_dir / "dialogue" / "normalized" / "dialogues.jsonl"

    if not jsonl_path.exists():
        click.echo(f"No dialogues found for project {project_id}")
        return

    click.echo(f"\nDialogues (showing first {limit}):\n")
    click.echo("-" * 80)

    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= limit:
                break

            dialogue = json.loads(line)
            start_min = int(dialogue['start'] // 60)
            start_sec = int(dialogue['start'] % 60)
            time_str = f"{start_min:02d}:{start_sec:02d}"

            click.echo(f"[{time_str}] {dialogue.get('normalized_text', dialogue.get('source_text', ''))}")

    click.echo("-" * 80)


@subtitle.command()
@click.argument('project_id')
def reset(project_id):
    """
    重置字幕处理（删除对话数据）

    PROJECT_ID: 项目ID
    """
    import shutil

    project_dir = Path(f"data/projects/{project_id}")
    dialogue_dir = project_dir / "dialogue"

    if not dialogue_dir.exists():
        click.echo(f"No dialogue data found for project {project_id}")
        return

    if click.confirm(f"Are you sure you want to reset subtitle data for {project_id}?"):
        shutil.rmtree(dialogue_dir)
        click.echo(f"✅ Subtitle data reset for project {project_id}")


if __name__ == '__main__':
    subtitle()
