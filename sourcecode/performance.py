import cProfile
import simulation
import pstats
import io


def prof_to_csv(prof: cProfile.Profile):
    out_stream = io.StringIO()
    pstats.Stats(prof, stream=out_stream).print_stats()
    result = out_stream.getvalue()
    # chop off header lines
    result = 'ncalls' + result.split('ncalls')[-1]
    lines = [','.join(line.rstrip().split(None, 5))
             for line in result.split('\n')]
    return '\n'.join(lines)


if __name__ == "__main__":
    pr = cProfile.Profile()
    pr.enable()
    # main()
    simulation.main()
    pr.disable()
    csv = prof_to_csv(pr)
    with open("prof.csv", 'w+') as f:
        f.write(csv)
