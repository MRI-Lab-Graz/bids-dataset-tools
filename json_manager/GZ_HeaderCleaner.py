#!/usr/bin/env python3
# clean_gzip_mtime_fname.py
from pathlib import Path
import os, sys, struct, argparse

# GZIP Flags
FHCRC    = 0x02
FEXTRA   = 0x04
FNAME    = 0x08
FCOMMENT = 0x10

def parse_gzip_header(f):
    """
    Liest den GZIP-Header am aktuellen Dateipointer.
    Rückgabe: (first10, flags, mtime, offsets dict)
      offsets = {
        'start': 0,
        'after_fixed': 10,
        'extra_len_off': pos oder None,
        'extra_end': pos nach EXTRA,
        'fname_start': pos oder None,
        'fname_end': pos (inkl. 0x00) oder None,
        'fcomment_start': pos oder None,
        'fcomment_end': pos (inkl. 0x00) oder None,
        'fhcrc_off': pos oder None,
        'payload_start': pos (Start der komprimierten Daten)
      }
    """
    start = f.tell()
    h = f.read(10)
    if len(h) < 10 or h[:2] != b"\x1f\x8b" or h[2] != 0x08:
        raise ValueError("Not a gzip member")
    flg = h[3]
    mtime = struct.unpack("<I", h[4:8])[0]
    idx = start + 10

    extra_len_off = None
    extra_end = None
    fname_start = fname_end = None
    fcomment_start = fcomment_end = None
    fhcrc_off = None

    # FEXTRA
    if flg & FEXTRA:
        extra_len_off = idx
        raw = f.read(2); idx += 2
        if len(raw) < 2:
            raise ValueError("Truncated EXTRA length")
        xlen = struct.unpack("<H", raw)[0]
        f.seek(xlen, os.SEEK_CUR); idx += xlen
        extra_end = idx

    # FNAME (C-String)
    if flg & FNAME:
        fname_start = idx
        while True:
            b = f.read(1)
            if not b:
                raise ValueError("Truncated FNAME")
            idx += 1
            if b == b"\x00":
                fname_end = idx
                break

    # FCOMMENT (C-String)
    if flg & FCOMMENT:
        fcomment_start = idx
        while True:
            b = f.read(1)
            if not b:
                raise ValueError("Truncated FCOMMENT")
            idx += 1
            if b == b"\x00":
                fcomment_end = idx
                break

    # FHCRC (2 Bytes)
    if flg & FHCRC:
        fhcrc_off = idx
        f.seek(2, os.SEEK_CUR); idx += 2

    payload_start = idx
    return (h, flg, mtime, {
        'start': start,
        'after_fixed': start + 10,
        'extra_len_off': extra_len_off,
        'extra_end': extra_end,
        'fname_start': fname_start,
        'fname_end': fname_end,
        'fcomment_start': fcomment_start,
        'fcomment_end': fcomment_end,
        'fhcrc_off': fhcrc_off,
        'payload_start': payload_start
    })

def needs_cleaning(path: Path):
    with open(path, "rb") as f:
        h, flg, mtime, _ = parse_gzip_header(f)
    need_mtime = (mtime != 0)
    need_fname = bool(flg & FNAME)
    need_fhcrc = bool(flg & FHCRC)  # nur relevant falls wir was ändern
    return need_mtime, need_fname, need_fhcrc, flg, mtime

def rewrite_header_only(inf, outf, meta):
    """
    Schreibt einen neuen Header, der NUR MTIME=0 setzt und das FNAME-Feld entfernt.
    - FEXTRA und FCOMMENT bleiben unverändert erhalten.
    - Falls FHCRC vorhanden war, wird es ENTFERNT (Flag löschen + 2 Bytes weglassen),
      damit die Datei konsistent bleibt (wir ändern ja den Header).
    """
    (first10, flg, mtime, off) = meta

    # Flags anpassen: FNAME löschen; FHCRC ebenfalls löschen (falls gesetzt)
    new_flg = flg & ~FNAME
    if flg & FHCRC:
        new_flg &= ~FHCRC
        drop_fhcrc = True
    else:
        drop_fhcrc = False

    # Fixed 10-Byte Header neu aufbauen (mit mtime=0, neuen Flags)
    new_fixed = bytearray(first10)
    new_fixed[3] = new_flg
    new_fixed[4:8] = b"\x00\x00\x00\x00"  # MTIME = 0

    # Schreiben: fixed
    outf.write(new_fixed)

    # Danach optionale Felder (in Originalreihenfolge), aber ohne FNAME und ggf. ohne FHCRC
    # 1) FEXTRA (wenn vorhanden): Bytes 2-Byte Länge + Daten unverändert kopieren
    if flg & FEXTRA:
        inf.seek(off['extra_len_off'])
        # EXTRA len + payload bis extra_end
        outf.write(inf.read(off['extra_end'] - off['extra_len_off']))

    # 2) FCOMMENT (falls vorhanden): unverändert kopieren
    if flg & FCOMMENT:
        inf.seek(off['fcomment_start'])
        outf.write(inf.read(off['fcomment_end'] - off['fcomment_start']))

    # (FNAME lassen wir aus → entfernt)

    # 3) FHCRC ggf. auslassen
    payload_from = off['payload_start']
    if drop_fhcrc and off['fhcrc_off'] is not None:
        # Payload start verschiebt sich um 2, weil wir FHCRC weglassen
        payload_from = off['fhcrc_off'] + 2

    # Rest der Datei (komprimierte Daten + Trailer + evtl. weitere Members) 1:1 kopieren
    inf.seek(payload_from, os.SEEK_SET)
    BUF = 1024 * 1024
    while True:
        chunk = inf.read(BUF)
        if not chunk:
            break
        outf.write(chunk)

def clean_file(path: Path):
    with open(path, "rb") as inf:
        meta = parse_gzip_header(inf)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "wb") as outf:
            rewrite_header_only(inf, outf, meta)
        os.replace(tmp, path)

def main():
    ap = argparse.ArgumentParser(description="Setzt GZIP MTIME=0 und entfernt FNAME (nur Dateien unter func/).")
    ap.add_argument("rawdata", help="Pfad zu rawdata (rekursiv durchsucht)")
    ap.add_argument("--dry-run", action="store_true", help="Nur prüfen, nichts ändern")
    args = ap.parse_args()

    root = Path(args.rawdata)
    if not root.exists():
        print(f"Pfad nicht gefunden: {root}", file=sys.stderr)
        sys.exit(1)

    targets = [p for p in root.rglob("*.gz") if "func" in p.parts]
    if not targets:
        print("Keine *.gz-Dateien unter func/ gefunden.")
        return

    total = changed = ok = errors = 0
    for p in sorted(targets):
        total += 1
        try:
            need_mtime, need_fname, need_fhcrc, flg, mtime = needs_cleaning(p)
        except Exception as e:
            print(f"[FEHLER] {p} -> {e}")
            errors += 1
            continue

        if need_mtime or need_fname:
            tag = []
            if need_mtime: tag.append(f"MTIME={mtime}")
            if need_fname: tag.append("FNAME")
            if need_fhcrc: tag.append("FHCRC(removal)")
            if args.dry_run:
                print(f"[WOERDE] {p}  ({', '.join(tag)})")
            else:
                try:
                    # tatsächliche Änderung
                    clean_file(p)
                    print(f"[FIXED ] {p}  ({', '.join(tag)})")
                    changed += 1
                except Exception as e:
                    print(f"[FEHLER] {p} -> {e}")
                    errors += 1
        else:
            ok += 1
            if args.dry_run:
                print(f"[OK    ] {p}  (flags OK, mtime=0)")

    print("\nZusammenfassung:")
    print(f"  Gefunden : {total}")
    print(f"  Geändert : {changed}" + (" (nur simuliert)" if args.dry_run else ""))
    print(f"  Clean    : {ok}")
    print(f"  Fehler   : {errors}")

if __name__ == "__main__":
    main()
