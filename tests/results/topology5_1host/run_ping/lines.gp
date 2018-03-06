set xlabel "Seconds"
set ylabel "RTT"
set ytics 10
set mytics 10
set format y "%.0sms"
set yrange [30:60]
set xtics 25
plot "lines.dat" using 1:2 title 'Client1' with lines, "lines.dat" using 1:3 title 'Client2' with lines, "lines.dat" using 1:4 title 'Client3' with lines
