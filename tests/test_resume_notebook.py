import io
import json
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from src.observability import configure_observability, traced
from src.observability.notebook import get_trace_url, read_uploaded_resume, run_resume_intake


class ResumeNotebookTests(unittest.TestCase):
    def setUp(self):
        self.stream = io.StringIO()
        configure_observability(stream=self.stream, tracing_enabled=False)

    def tearDown(self):
        configure_observability(stream=io.StringIO(), tracing_enabled=False)

    def test_text_upload_and_invalid_formats(self):
        self.assertEqual(read_uploaded_resume("resume.md", memoryview(b" Resume text \n")), "Resume text")
        for name, content in [("resume.txt", b""), ("resume.txt", b"  "),
                              ("resume.txt", b"\xff"), ("resume.docx", b"text")]:
            with self.subTest(name=name, content=content), self.assertRaises(ValueError):
                read_uploaded_resume(name, content)

    def test_pdf_conversion_uses_temp_path_and_cleans_up(self):
        paths = []
        def convert(arguments, **options):
            paths.extend([Path(arguments[2]), Path(arguments[3])])
            self.assertEqual(paths[0].name, "resume.pdf")
            self.assertEqual(options["timeout"], 30)
            paths[1].write_text("PDF resume text")
        with patch("src.observability.notebook.shutil.which", return_value="/usr/bin/pdftotext"), patch(
            "src.observability.notebook.subprocess.run", side_effect=convert
        ):
            self.assertEqual(read_uploaded_resume("../../private-name.pdf", b"%PDF"), "PDF resume text")
        self.assertTrue(all(not p.exists() for p in paths))

    def test_intake_is_one_trace_and_keeps_resume_out_of_logs(self):
        resume = SimpleNamespace(name="Private Name")
        analysis = SimpleNamespace(competency_evidence=[1, 2])
        extract = Mock(return_value=resume)
        analyze = Mock(return_value=analysis)
        modules = {
            "src.resume.extractor": SimpleNamespace(extract_resume=traced("resume.extract")(extract)),
            "src.resume.analyzer": SimpleNamespace(analyze_resume=traced("resume.analyze")(analyze)),
        }
        with patch.dict("sys.modules", modules), patch("src.observability.notebook.flush_telemetry") as flush:
            result = run_resume_intake("private resume text", interview_id="intake-test")
        self.assertIs(result["resume"], resume)
        analyze.assert_called_once_with(resume)
        self.assertTrue(extract.call_args.kwargs["candidate_id"].startswith("candidate-"))
        flush.assert_called_once_with(timeout=5.0)
        logs = [json.loads(line) for line in self.stream.getvalue().splitlines()]
        self.assertTrue(all(r["trace_id"] == result["trace_id"] for r in logs))
        self.assertNotIn("private resume text", self.stream.getvalue())
        self.assertNotIn("Private Name", self.stream.getvalue())
        self.assertEqual({r["attributes"].get("operation") for r in logs},
                         {"intake.resume", "resume.extract", "resume.analyze"})

    def test_failure_flushes_without_losing_original_error(self):
        error = RuntimeError("private provider response")
        with patch.dict("sys.modules", {
            "src.resume.extractor": SimpleNamespace(extract_resume=Mock(side_effect=error)),
            "src.resume.analyzer": SimpleNamespace(analyze_resume=Mock()),
        }), patch("src.observability.notebook.flush_telemetry") as flush:
            with self.assertRaises(RuntimeError) as caught:
                run_resume_intake("text")
        self.assertIs(caught.exception, error)
        flush.assert_called_once()
        self.assertNotIn("private provider response", self.stream.getvalue())

    def test_trace_link_lookup_does_not_create_public_share(self):
        with patch("langsmith.run_trees.get_cached_client") as client:
            client.return_value.get_run_url.return_value = "https://smith.langchain.com/test"
            self.assertEqual(get_trace_url("trace-id"), "https://smith.langchain.com/test")
            client.return_value.read_run.assert_called_once_with("trace-id")
            client.return_value.share_run.assert_not_called()
            client.return_value.read_run.side_effect = RuntimeError("private connection details")
            self.assertIsNone(get_trace_url("trace-id"))
        self.assertNotIn("private connection details", self.stream.getvalue())

    def test_notebook_is_valid_and_has_no_saved_outputs(self):
        import nbformat
        path = Path(__file__).resolve().parents[1] / "notebooks/02_resume_langsmith.ipynb"
        notebook = nbformat.read(path, as_version=4)
        nbformat.validate(notebook)
        for index, cell in enumerate(notebook.cells):
            if cell.cell_type == "code":
                compile(cell.source, f"cell-{index}", "exec")
                self.assertEqual(cell.outputs, [])
                self.assertIsNone(cell.execution_count)

    def test_upload_run_cell_with_widget_and_mock_pipeline(self):
        import contextlib
        import ipywidgets as widgets
        from datetime import datetime, timezone
        path = Path(__file__).resolve().parents[1] / "notebooks/02_resume_langsmith.ipynb"
        notebook = json.loads(path.read_text())
        upload = widgets.FileUpload(value=[{
            "name": "new-resume.txt", "type": "text/plain", "size": 11,
            "content": memoryview(b"Resume text"), "last_modified": datetime.now(timezone.utc),
        }])
        pipeline = Mock(return_value={
            "trace_id": "test-trace", "analysis": SimpleNamespace(competency_evidence=[]),
        })
        namespace = {"upload": upload, "read_uploaded_resume": read_uploaded_resume,
                     "run_resume_intake": pipeline}
        with contextlib.redirect_stdout(io.StringIO()):
            exec("".join(notebook["cells"][5]["source"]), namespace)
        self.assertEqual(upload.value, ())
        self.assertEqual(pipeline.call_args.args, ("Resume text",))
        self.assertFalse(pipeline.call_args.kwargs["include_interview"])
        self.assertNotIn("resume_text", namespace)

    def test_optional_interview_pipeline(self):
        plan = SimpleNamespace()
        questions = SimpleNamespace(questions=[1, 2], is_complete=False)
        select = Mock(return_value=questions)
        with patch.dict("sys.modules", {
            "src.resume.extractor": SimpleNamespace(extract_resume=Mock(return_value=SimpleNamespace())),
            "src.resume.analyzer": SimpleNamespace(analyze_resume=Mock(return_value=SimpleNamespace(competency_evidence=[]))),
            "src.planning.interview_planner": SimpleNamespace(create_interview_plan=Mock(return_value=plan)),
            "src.interview.question_selector": SimpleNamespace(select_interview_questions=select),
        }):
            result = run_resume_intake("Resume text", include_interview=True)
        select.assert_called_once_with(plan)
        self.assertIs(result["question_set"], questions)


if __name__ == "__main__":
    unittest.main()
