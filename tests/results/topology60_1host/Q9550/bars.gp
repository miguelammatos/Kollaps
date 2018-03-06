set ylabel "Throughput"
set ytics 10000000
set mytics 10
set format y "%.0s%cbit/s"
set style data histogram
set style histogram errorbars gap 1 lw 1
set style fill solid 0.5
set boxwidth 0.9
plot "bars.dat" using 2:3:4:xtic(1) lc rgb "#DAA520" title "Mean throughput"
