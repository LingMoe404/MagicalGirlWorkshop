"""Pure-function tests for workers/command_builder.py.

Locks the exact argv sequences produced by the command construction helpers
that were extracted from EncoderWorker (S1). No Qt / subprocess / signal
required. The same sequences are also asserted end-to-end by the argv snapshot
tests in tests/test_encoder.py.

command_builder is transitively Qt-free: it imports no config.py (which pulls in
PySide6). Protocol constants (audio codec/sample rate, loudnorm modes, color
modes) are passed explicitly by EncoderWorker; several tests below pass the same
constants explicitly to prove the parameterized path behaves identically to the
module defaults.
"""

import os
import unittest

from workers.command_builder import (
    build_ab_av1_search_cmd,
    build_audio_args,
    build_color_args,
    build_subtitle_args,
    build_video_encoder_args,
    should_apply_loudnorm,
)


class BuildAbAv1SearchCmdTests(unittest.TestCase):
    def test_hardware_strategy_order(self):
        cmd = build_ab_av1_search_cmd(
            "C:/tools/ab-av1.exe",
            "D:/input.mkv",
            encoder="av1_qsv",
            pix_fmt="yuv420p10le",
            target_vmaf="93.0",
            preset="4",
            max_crf="51",
        )
        self.assertEqual(
            cmd,
            [
                "C:/tools/ab-av1.exe",
                "crf-search",
                "-i",
                "D:/input.mkv",
                "--encoder",
                "av1_qsv",
                "--pix-format",
                "yuv420p10le",
                "--min-vmaf",
                "93.0",
                "--preset",
                "4",
                "--max-crf",
                "51",
            ],
        )

    def test_max_crf_is_passed_verbatim(self):
        cmd = build_ab_av1_search_cmd(
            "ab-av1.exe",
            "in.mkv",
            encoder="libsvtav1",
            pix_fmt="yuv420p10le",
            target_vmaf="93.0",
            preset="9",
            max_crf="63",
        )
        self.assertEqual(cmd[cmd.index("--max-crf") + 1], "63")

    def test_target_vmaf_is_stringified(self):
        cmd = build_ab_av1_search_cmd(
            "ab-av1.exe",
            "in.mkv",
            encoder="av1_nvenc",
            pix_fmt="yuv420p10le",
            target_vmaf=93.0,
            preset="p4",
            max_crf="51",
        )
        self.assertEqual(cmd[cmd.index("--min-vmaf") + 1], "93.0")

    def test_temp_dir_appended_only_when_dir_exists(self):
        existing = os.path.dirname(os.path.abspath(__file__))
        with_temp = build_ab_av1_search_cmd(
            "ab-av1.exe",
            "in.mkv",
            encoder="av1_qsv",
            pix_fmt="yuv420p10le",
            target_vmaf="93.0",
            preset="4",
            max_crf="51",
            cache_dir=existing,
        )
        self.assertIn("--temp-dir", with_temp)
        self.assertEqual(with_temp[with_temp.index("--temp-dir") + 1], existing)

        without_temp = build_ab_av1_search_cmd(
            "ab-av1.exe",
            "in.mkv",
            encoder="av1_qsv",
            pix_fmt="yuv420p10le",
            target_vmaf="93.0",
            preset="4",
            max_crf="51",
            cache_dir="Z:/definitely/not/a/real/dir",
        )
        self.assertNotIn("--temp-dir", without_temp)


class BuildAudioArgsTests(unittest.TestCase):
    def test_basic_audio_block(self):
        self.assertEqual(
            build_audio_args("96k", "", "Disable", 2),
            ["-c:a", "libopus", "-b:a", "96k", "-ar", "48000"],
        )

    def test_loudnorm_applied_when_always(self):
        args = build_audio_args("96k", "loudnorm=I=-16:TP=-1.5:LRA=11", "Always", 6)
        self.assertIn("-af", args)
        self.assertEqual(
            args[args.index("-af") + 1],
            "loudnorm=I=-16:TP=-1.5:LRA=11,aformat=channel_layouts=5.1",
        )

    def test_auto_skips_loudnorm_for_multichannel(self):
        args = build_audio_args(
            "96k",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "Stereo/Mono Only",
            6,
        )
        self.assertIn("-af", args)
        self.assertEqual(
            args[args.index("-af") + 1],
            "aformat=channel_layouts=5.1",
        )

    def test_auto_applies_loudnorm_for_stereo(self):
        args = build_audio_args(
            "96k",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "Stereo/Mono Only",
            2,
        )
        self.assertIn("-af", args)
        self.assertEqual(
            args[args.index("-af") + 1],
            "loudnorm=I=-16:TP=-1.5:LRA=11",
        )

    def test_auto_applies_loudnorm_when_channels_unknown(self):
        args = build_audio_args(
            "96k",
            "loudnorm=I=-16:TP=-1.5:LRA=11",
            "Stereo/Mono Only",
            None,
        )
        self.assertIn("-af", args)

    def test_8ch_gets_71_layout(self):
        args = build_audio_args("96k", "loudnorm=I=-16", "Always", 8)
        self.assertEqual(
            args[args.index("-af") + 1],
            "loudnorm=I=-16,aformat=channel_layouts=7.1",
        )

    def test_loudnorm_empty_but_channels_known(self):
        args = build_audio_args("96k", "", "Always", 6)
        self.assertIn("-af", args)
        self.assertEqual(args[args.index("-af") + 1], "aformat=channel_layouts=5.1")

    def test_no_filters_when_nothing_applies(self):
        # 6ch always gets the aformat filter even with loudnorm disabled
        args = build_audio_args("96k", "", "Disable", 6)
        self.assertIn("-af", args)
        self.assertEqual(args[args.index("-af") + 1], "aformat=channel_layouts=5.1")
        # 2ch with nothing applicable has no filter
        args = build_audio_args("96k", "", "Disable", 2)
        self.assertNotIn("-af", args)

    def test_explicit_protocol_constants(self):
        # EncoderWorker passes audio_codec/sample_rate/loudnorm-mode constants
        # from config explicitly; behavior must match the defaults.
        args = build_audio_args(
            "96k",
            "loudnorm=I=-16",
            "Always",
            6,
            audio_codec="libopus",
            sample_rate="48000",
            loudnorm_mode_always="Always",
            loudnorm_mode_auto="Stereo/Mono Only",
        )
        self.assertEqual(
            args,
            [
                "-c:a",
                "libopus",
                "-b:a",
                "96k",
                "-ar",
                "48000",
                "-af",
                "loudnorm=I=-16,aformat=channel_layouts=5.1",
            ],
        )


class BuildColorArgsTests(unittest.TestCase):
    def test_sdr_auto_returns_no_args_and_not_hdr(self):
        args, is_hdr = build_color_args("Auto", "bt709", "bt709", "bt709", False)
        self.assertEqual(args, [])
        self.assertFalse(is_hdr)

    def test_force_sdr_hdr_source_returns_no_args(self):
        # Force SDR (COLOR_MODE_SDR) must never emit tone-map or color tags,
        # even when the source is HDR.
        args, is_hdr = build_color_args("SDR", "smpte2084", "bt2020nc", "bt2020", False)
        self.assertEqual(args, [])
        self.assertTrue(is_hdr)

    def test_force_sdr_hdr_source_no_args_with_protocol_constants(self):
        # Same as above, passing protocol constants explicitly (as EncoderWorker does).
        args, is_hdr = build_color_args(
            "SDR",
            "smpte2084",
            "bt2020nc",
            "bt2020",
            False,
            color_mode_auto="Auto",
            color_mode_tonemap="ToneMap",
        )
        self.assertEqual(args, [])
        self.assertTrue(is_hdr)

    def test_hdr_auto_returns_color_tags(self):
        args, is_hdr = build_color_args(
            "Auto", "smpte2084", "bt2020nc", "bt2020", False
        )
        self.assertTrue(is_hdr)
        self.assertEqual(
            args,
            [
                "-color_primaries",
                "bt2020",
                "-color_trc",
                "smpte2084",
                "-colorspace",
                "bt2020nc",
            ],
        )

    def test_hdr_auto_fills_missing_values(self):
        args, is_hdr = build_color_args("Auto", "", "", "", True)
        self.assertTrue(is_hdr)
        self.assertEqual(
            args,
            [
                "-color_primaries",
                "bt2020",
                "-color_trc",
                "smpte2084",
                "-colorspace",
                "bt2020nc",
            ],
        )

    def test_hlg_transfer_counts_as_hdr(self):
        args, is_hdr = build_color_args(
            "Auto", "arib-std-b67", "bt2020nc", "bt2020", False
        )
        self.assertTrue(is_hdr)
        self.assertIn("-color_trc", args)

    def test_tonemap_hdr_returns_vf_filter(self):
        args, is_hdr = build_color_args(
            "ToneMap", "smpte2084", "bt2020nc", "bt2020", False
        )
        self.assertTrue(is_hdr)
        self.assertEqual(
            args,
            [
                "-vf",
                (
                    "zscale=t=linear:npl=100,format=gbrpf32,"
                    "zscale=p=bt709:t=bt709:m=bt709:r=limited,"
                    "format=yuv420p10le"
                ),
            ],
        )

    def test_tonemap_hdr_protocol_constants(self):
        args, is_hdr = build_color_args(
            "ToneMap",
            "smpte2084",
            "bt2020nc",
            "bt2020",
            False,
            color_mode_auto="Auto",
            color_mode_tonemap="ToneMap",
        )
        self.assertTrue(is_hdr)
        self.assertEqual(
            args,
            [
                "-vf",
                (
                    "zscale=t=linear:npl=100,format=gbrpf32,"
                    "zscale=p=bt709:t=bt709:m=bt709:r=limited,"
                    "format=yuv420p10le"
                ),
            ],
        )

    def test_tonemap_sdr_returns_no_args(self):
        args, is_hdr = build_color_args("ToneMap", "bt709", "bt709", "bt709", False)
        self.assertEqual(args, [])
        self.assertFalse(is_hdr)


class BuildVideoEncoderArgsTests(unittest.TestCase):
    def test_qsv(self):
        self.assertEqual(
            build_video_encoder_args("av1_qsv", 30, "4"),
            ["-global_quality:v", "30", "-preset", "4", "-look_ahead", "1"],
        )

    def test_nvenc_with_aq(self):
        self.assertEqual(
            build_video_encoder_args("av1_nvenc", 30, "p4", nv_aq=True),
            [
                "-cq",
                "30",
                "-preset",
                "p4",
                "-b:v",
                "0",
                "-spatial-aq",
                "1",
                "-temporal-aq",
                "1",
            ],
        )

    def test_nvenc_without_aq(self):
        self.assertEqual(
            build_video_encoder_args("av1_nvenc", 30, "p4", nv_aq=False),
            ["-cq", "30", "-preset", "p4", "-b:v", "0"],
        )

    def test_amf_with_preanalysis(self):
        self.assertEqual(
            build_video_encoder_args("av1_amf", 30, "balanced", nv_aq=True),
            [
                "-usage",
                "transcoding",
                "-quality",
                "balanced",
                "-rc",
                "vbr_latency",
                "-qvbr_quality_level",
                "30",
                "-preanalysis",
                "true",
            ],
        )

    def test_amf_without_preanalysis(self):
        self.assertEqual(
            build_video_encoder_args("av1_amf", 30, "quality", nv_aq=False),
            [
                "-usage",
                "transcoding",
                "-quality",
                "quality",
                "-rc",
                "vbr_latency",
                "-qvbr_quality_level",
                "30",
            ],
        )

    def test_icq_is_stringified(self):
        args = build_video_encoder_args("av1_qsv", 24, "2")
        self.assertEqual(args[args.index("-global_quality:v") + 1], "24")


class BuildSubtitleArgsTests(unittest.TestCase):
    def test_included_copy(self):
        self.assertEqual(
            build_subtitle_args(True, "copy"),
            ["-c:s", "copy", "-map", "0:v:0", "-map", "0:a", "-map", "0:s?"],
        )

    def test_included_subrip(self):
        self.assertEqual(
            build_subtitle_args(True, "subrip"),
            ["-c:s", "subrip", "-map", "0:v:0", "-map", "0:a", "-map", "0:s?"],
        )

    def test_excluded(self):
        self.assertEqual(
            build_subtitle_args(False, "copy"),
            ["-sn", "-map", "0:v:0", "-map", "0:a"],
        )


class ShouldApplyLoudnormTests(unittest.TestCase):
    def test_always_applies_regardless_of_channels(self):
        self.assertTrue(should_apply_loudnorm("Always", 8))
        self.assertTrue(should_apply_loudnorm("Always", None))

    def test_auto_applies_for_stereo_or_unknown(self):
        self.assertTrue(should_apply_loudnorm("Stereo/Mono Only", 2))
        self.assertTrue(should_apply_loudnorm("Stereo/Mono Only", 1))
        self.assertTrue(should_apply_loudnorm("Stereo/Mono Only", None))

    def test_auto_skips_multichannel(self):
        self.assertFalse(should_apply_loudnorm("Stereo/Mono Only", 6))
        self.assertFalse(should_apply_loudnorm("Stereo/Mono Only", 8))

    def test_disable_never_applies(self):
        self.assertFalse(should_apply_loudnorm("Disable", 2))
        self.assertFalse(should_apply_loudnorm("Disable", None))

    def test_explicit_protocol_constants(self):
        # EncoderWorker passes the config constants explicitly; behavior identical.
        self.assertTrue(
            should_apply_loudnorm("Always", 8, "Always", "Stereo/Mono Only")
        )
        self.assertTrue(
            should_apply_loudnorm("Stereo/Mono Only", 2, "Always", "Stereo/Mono Only")
        )
        self.assertFalse(
            should_apply_loudnorm("Stereo/Mono Only", 8, "Always", "Stereo/Mono Only")
        )
        self.assertFalse(
            should_apply_loudnorm("Disable", 2, "Always", "Stereo/Mono Only")
        )


if __name__ == "__main__":
    unittest.main()
