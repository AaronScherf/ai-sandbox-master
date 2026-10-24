import contextlib
import copy
import io
import sqlite3
import tempfile
import unittest
from pathlib import Path

from agent.literature import contribute, db
from agent.literature.cli import main
from agent.literature.cluster import define_cluster, save_cluster
from core.agent_tasks.work import task_entry
from lit_helpers import VOCABS, good, write_vocab_dir
from synth_helpers import F1, F2, F3, PROV, _answer, build, three_papers, with_sector


def dump(conn):
    return {t: sorted(conn.execute(f"SELECT * FROM {t}").fetchall(), key=repr)
            for t in ("papers", "facts", "results", "annotations", "cluster_members")}


class TestDb(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.target, self.papers = build(self.tmp.name, three_papers())
        cluster = define_cluster(self.target.records, VOCABS, "demo", ["sector=social protection"])
        save_cluster(self.tmp.name, cluster)
        for t in contribute.make_tasks(self.target, cluster, self.papers)[0]:
            contribute.apply_result(self.target, task_entry(t), _answer(), PROV)
        self.path = db.db_path(self.tmp.name)
        self.counts = db.build(self.target, self.path)
        self.conn = sqlite3.connect(self.path)
        self.addCleanup(self.conn.close)

    def test_build_loads_every_table(self):
        self.assertEqual(self.counts["papers"], 3)
        self.assertEqual(self.counts["results"], 3)
        self.assertEqual(self.counts["annotations"], 2)
        self.assertEqual(self.counts["cluster_members"], 2)
        row = self.conn.execute("SELECT title, year FROM papers WHERE file_id=?", (F1,)).fetchone()
        self.assertEqual(row, (f"Paper {F1}", 2019))
        tiers = {r[0] for r in self.conn.execute("SELECT tier FROM facts")}
        self.assertEqual(tiers, {"A"})

    def test_rebuilding_gives_identical_rows(self):
        first = dump(self.conn)
        self.conn.close()  # Windows cannot replace an open file
        db.build(self.target, self.path)
        conn = sqlite3.connect(self.path)
        self.addCleanup(conn.close)
        self.assertEqual(dump(conn), first)

    def test_matrix_counts_papers_per_intervention_outcome_design(self):
        rows = {(r["intervention"], r["outcome"], r["study_design"]): r["papers"] for r in db.matrix(self.conn)}
        self.assertEqual(rows[("cash transfer", "food consumption", "panel")], 2)
        self.assertEqual(sum(rows.values()), 3)

    def test_distribution_by_facet(self):
        self.assertEqual(db.distribution(self.conn, "countries"), [("SO", 3)])
        self.assertEqual(dict(db.distribution(self.conn, "study_design")), {"panel": 3})
        with self.assertRaises(ValueError):
            db.distribution(self.conn, "nonsense")

    def test_query_uses_the_cluster_matching_rules(self):
        ids = lambda *w: [r["file_id"] for r in db.query(self.conn, VOCABS, list(w))]
        self.assertEqual(ids("intervention=cash transfer"), [F1, F3])
        self.assertEqual(ids("countries=so"), [F1, F2, F3])
        self.assertEqual(ids("sector=social protection", "intervention=voucher"), [])
        with self.assertRaises(ValueError):
            ids("intervention=not a term")

    def test_export_writes_a_markdown_matrix(self):
        out = Path(self.tmp.name) / "matrix.md"
        db.export_markdown(self.conn, out)
        text = out.read_text(encoding="utf-8")
        self.assertIn("| Intervention | Outcome | Study design | Papers |", text)
        self.assertIn("| cash transfer | food consumption | panel | 2 |", text)


class TestCooccurrence(unittest.TestCase):
    def test_pairs_of_data_sources_in_one_paper(self):
        with tempfile.TemporaryDirectory() as root:
            two = with_sector(good())
            two["core"]["data_sources"].append({"value": "ACLED", "proposed": True,
                                                "quote": "FSNAU food security surveys collected at district level", "locator": 2})
            target, _ = build(root, {F1: two, F2: copy.deepcopy(good())})
            path = db.db_path(root)
            db.build(target, path)
            conn = sqlite3.connect(path)
            try:
                self.assertEqual(db.cooccurrence(conn), [("ACLED", "fsnau", 1)])
            finally:
                conn.close()


class TestDbCli(unittest.TestCase):
    def test_build_then_matrix_and_query(self):
        with tempfile.TemporaryDirectory() as root:
            build(root, three_papers())
            vocab_dir = Path(root) / "vocab"
            vocab_dir.mkdir()
            write_vocab_dir(vocab_dir)

            def run(*args):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = main(["--index-root", root, "--vocab-dir", str(vocab_dir), *args])
                return code, out.getvalue()

            self.assertEqual(run("db", "matrix")[0], 2)  # nothing built yet
            code, out = run("db", "build")
            self.assertEqual(code, 0)
            self.assertIn("3 papers", out)
            code, out = run("db", "matrix")
            self.assertIn("cash transfer", out)
            code, out = run("db", "query", "--where", "intervention=voucher")
            self.assertIn(F2, out)
            self.assertNotIn(F1, out)
            self.assertEqual(run("db", "dist", "countries")[1].strip(), "SO\t3")


if __name__ == "__main__":
    unittest.main()
