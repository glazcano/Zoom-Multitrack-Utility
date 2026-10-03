import sys

if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] in ('--verify', '--verify-no-audio'):
        from h8studio.verify import verify
        raise SystemExit(verify(sys.argv[2], sys.argv[3], audio=sys.argv[1] == '--verify'))
    from h8studio.ui import run
    raise SystemExit(run())
