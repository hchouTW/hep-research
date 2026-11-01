"""A cooperative stand-in backend program for the detector-simulation shared layer tests (TASK.md 5.8 Do 2).

Copied by the tests into ENV_ROOT/bin/synthetic-sim (with this interpreter in its first line). It is called as the
synthetic backend's ExecutionSpec says: synthetic-sim CONFIG --input INPUT --out VALUES. Its behaviour comes from the
file $SYNTHETIC_DATA/mode (one word, optional second word = an argument), so a test changes the behaviour without
changing the plan:
  ok           write one row per event: "charge,<d>e<i>,e,<i>" (d from the seed), exit 0
  fail         write nothing, exit 3
  partial      exit 0 without writing the values file (native success, required content missing)
  empty        exit 0 with an empty values file
  sleep S      write $SYNTHETIC_DATA/started (its pid), sleep S seconds, then behave as ok
  bigout       write 4 MiB into raw/, then sleep 30 (the output budget aborts it)
  ignore_term  ignore SIGTERM, write started, sleep 30 (needs SIGKILL)
  grandchild   start a grandchild that sleeps 30 s and records its pid in $SYNTHETIC_DATA/grandchild, then ok
  modify_input make the input writable and append to it, then ok
  late S       write started, sleep S, then write raw/late.txt by relative path (an orphan's late write)
  group        fork a child in the same process group that records its pid in $SYNTHETIC_DATA/member and sleeps,
               write started, sleep 30 (a timeout must kill the whole group)
  selfkill     kill itself with SIGKILL (the backend ends by a signal)
Never used outside tests; no physics.
"""
import os
import signal
import sys
import time
from pathlib import Path


def main(argv):
    config, inp, out = Path(argv[0]), Path(argv[2]), Path(argv[4])
    data_dir = Path(os.environ["SYNTHETIC_DATA"])
    words = (data_dir / "mode").read_text(encoding="utf-8").split() if (data_dir / "mode").is_file() else ["ok"]
    mode, arg = words[0], (words[1] if len(words) > 1 else None)
    settings = dict(line.split(" = ", 1) for line in config.read_text(encoding="utf-8").splitlines() if " = " in line)
    events, seed = int(settings["events"]), int(settings["seed"])

    def write_ok():
        out.parent.mkdir(parents=True, exist_ok=True)
        digit = seed % 9 + 1
        out.write_text("".join(f"charge,{digit}e{i},e,{i}\n" for i in range(events)), encoding="utf-8")

    if mode == "fail":
        return 3
    if mode == "partial":
        return 0
    if mode == "empty":
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("", encoding="utf-8")
        return 0
    if mode in ("sleep", "ignore_term", "late"):
        if mode == "ignore_term":
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
        (data_dir / "started").write_text(str(os.getpid()), encoding="utf-8")
        time.sleep(float(arg or 30))
        if mode == "late":
            Path("raw").mkdir(exist_ok=True)
            Path("raw", "late.txt").write_text("written after the controller died\n", encoding="utf-8")
            return 0
    if mode == "bigout":
        out.parent.mkdir(parents=True, exist_ok=True)
        (out.parent / "big.bin").write_bytes(b"\0" * (4 << 20))
        time.sleep(30)
        return 0
    if mode == "selfkill":
        os.kill(os.getpid(), signal.SIGKILL)
    if mode == "group":
        if os.fork() == 0:
            (data_dir / "member").write_text(str(os.getpid()), encoding="utf-8")
            time.sleep(30)
            os._exit(0)
        (data_dir / "started").write_text(str(os.getpid()), encoding="utf-8")
        time.sleep(30)
        return 0
    if mode == "grandchild":
        pid = os.fork()
        if pid == 0:
            (data_dir / "grandchild").write_text(str(os.getpid()), encoding="utf-8")
            time.sleep(30)
            os._exit(0)
    if mode == "modify_input":
        os.chmod(inp, 0o644)
        with open(inp, "a", encoding="utf-8") as fh:
            fh.write("changed by the backend\n")
    write_ok()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
