d3.csv("../../data/portfolios/portfolio.csv").then(data => {
    // Parse the date for comparison
    const parseDate = d3.timeParse('%Y-%m-%d');
    data.forEach(d => {
        d.Date = parseDate(d.Date);
        d.weights = parseFloat(d.weights);
        d.holding_size = parseFloat(d.holding_size);
        d.holding_value = parseFloat(d.holding_value);
        d.Close = parseFloat(d.Close);
    });

    // Find the maximum date in the dataset
    const maxDate = d3.max(data, d => d.Date);

    // Filter data for the rows with the maximum date
    const recentData = data.filter(d => d.Date.getTime() === maxDate.getTime());

    const tableBody = d3.select("#portfolio-table tbody");

    // For each row in the recentData, append a row and cells to the table in HTML
    recentData.forEach(d => {
        if (d.weights > 0) {
            const row = tableBody.append("tr");
            
            // Append cells for each desired column
            row.append("td").text(d.ticker);
            row.append("td").text((d.position === "long" ? "+" : "-") + (d.weights*0.3).toFixed(2));
            row.append("td").text((d.position === "long" ? "+" : "") + d.holding_size.toFixed(2));
            row.append("td").text(d.holding_value.toLocaleString('en-US'));
            row.append("td").text(d.Close.toLocaleString('en-US'));
        }
    });

    // Filter data for long and short positions
    const longData = recentData.filter(d => d.position === "long" && d.weights > 0);
    const shortData = recentData.filter(d => d.position === "short" && d.weights > 0);

    // General function to draw pie chart
    function drawPieChart(data, elementId, radius) {
        const pie = d3.pie().value(d => d.weights)(data);
        const color = d3.scaleOrdinal(d3.schemeCategory10); // Color scheme

        const svg = d3.select(`#${elementId}`)
            .append("svg")
            .attr("width", radius * 2)
            .attr("height", radius * 2)
            .append("g")
            .attr("transform", `translate(${radius}, ${radius})`);

        const arc = d3.arc().innerRadius(0).outerRadius(radius);

        // Draw pie slices
        svg.selectAll("path")
            .data(pie)
            .enter()
            .append("path")
            .attr("d", arc)
            .attr("fill", (d, i) => color(i));

        // Add labels
        svg.selectAll("text")
            .data(pie)
            .enter()
            .append("text")
            .text(d => `${d.data.ticker} (${Math.round(d.data.weights * 100)}%)`)
            .attr("transform", d => `translate(${arc.centroid(d)})`)
            .style("text-anchor", "middle")
            .style("font-size", "12px");
    }

    // Drawing pie charts
    drawPieChart(longData, "pie-long", 200);    // Assuming radius 150 for the long pie
    drawPieChart(shortData, "pie-short", 150);   // Half the size for the short pie
});

d3.csv("../../data/portfolios/wealth.csv").then(data => {
    // Assuming the 'wealth' column is a numeric value, convert it
    data.forEach(d => {
        d.wealth = +d.wealth;
    });

    // Get the first and last value from the 'wealth' column
    const totalDeposits = data[0].wealth;
    const currentWealth = data[data.length - 1].wealth;

    // Compute the return
    const returnPercent = ((currentWealth - totalDeposits) / totalDeposits) * 100;
    const returnGain = currentWealth - totalDeposits;

    // Populate the HTML elements with the computed values
    d3.select("#total-deposits").text(totalDeposits.toLocaleString('en-US') + " CHF");
    d3.select("#current-wealth").text(currentWealth.toLocaleString('en-US') + " CHF");
    d3.select("#return-percent").text((returnPercent > 0 ? "+" : "-") + returnPercent.toFixed(2) + "%");
    d3.select("#return-gain").text((returnGain > 0 ? "+" : "-") + returnGain.toLocaleString('en-US') + " CHF");
});