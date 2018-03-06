set xlabel "Seconds"
set ylabel "Throughput"
set xtics 25
set format y "%.0s%cbit/s"
set ytics 10000000
set mytics 10
plot "lines.dat" using 1:2 title 'Client1' with lines, "lines.dat" using 1:3 title 'Client2' with lines, "lines.dat" using 1:4 title 'Client3' with lines, "lines.dat" using 1:5 title 'Total' with lines
