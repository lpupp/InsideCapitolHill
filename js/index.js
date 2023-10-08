// The SVG dimensions
const margin = {top: 20, right: 20, bottom: 50, left: 50},
width = 960 - margin.left - margin.right,
height = 500 - margin.top - margin.bottom;

// Parse the date
const parseDate = d3.timeParse('%Y-%m-%d');

// Set the scales
const x = d3.scaleTime().range([0, width]);
const y = d3.scaleLinear().range([height, 0]);

// Define the line for wealth
const valueline = d3.line()
    .x(d => x(d.date))
    .y(d => y(d.wealth));

// Define the line for wealth_spx
const valuelineSPX = d3.line()
    .x(d => x(d.date))
    .y(d => y(d.wealth_spx));

// Append an SVG to the returns-plot div
const svg = d3.select("#plot")
.append("svg")
.attr("width", width + margin.left + margin.right)
.attr("height", height + margin.top + margin.bottom)
.append("g")
.attr("transform", `translate(${margin.left},${margin.top})`);

// Get the data from the CSV
d3.csv("data/wealth.csv").then(data => {
    const totalDeposits = data[0].wealth;
    const currentWealth = data[data.length - 1].wealth;

    // Parse the date and convert wealth to number
    data.forEach(d => {
        d.date = parseDate(d.date);
        d.wealth = parseFloat(d.wealth) / parseFloat(totalDeposits);
        d.wealth_spx = parseFloat(d.wealth_spx) / parseFloat(totalDeposits);
    });

    // Set the domain for the scales
    x.domain(d3.extent(data, d => d.date));

    // Adjust y-domain to consider both wealth and wealth_spx
    y.domain([0, d3.max(data, d => Math.max(d.wealth, d.wealth_spx))]);

    // Add the path (the line for wealth)
    svg.append("path")
        .data([data])
        .attr("class", "line")
        .attr("d", valueline);

    // Add the path (the line for wealth_spx)
    svg.append("path")
        .data([data])
        .attr("class", "line-spx")
        .attr("d", valuelineSPX);

    // Add the X-axis
    svg.append("g")
    .attr("transform", `translate(0,${height})`)
    .call(d3.axisBottom(x));

    // Add the Y-axis
    svg.append("g")
    .call(d3.axisLeft(y));

    // const allDates = data.map(d => d.date).sort(d3.ascending); // Assuming 'date' is already parsed
    // const slider = d3.select("#date-slider")
    //                 .attr("max", allDates.length - 1)
    //                 .on("input", onSliderInput);

    // function onSliderInput() {
    //     const selectedDateIndex = +this.value; // Convert to number
    //     const selectedDate = allDates[selectedDateIndex];
    //     d3.select("#selected-date").text(selectedDate); // Display the selected date
    //     updateVisualization(selectedDate); // Function to update your visualization
    // }
    // Assuming the 'wealth' column is a numeric value, convert it
    data.forEach(d => {
        d.wealth = +d.wealth;
    });

    // Compute the return
    const returnPercent = ((currentWealth - totalDeposits) / totalDeposits) * 100;
    const returnGain = currentWealth - totalDeposits;

    // Populate the HTML elements with the computed values
    d3.select("#total-deposits").text(totalDeposits.toLocaleString('en-US') + " CHF");
    d3.select("#current-wealth").text(currentWealth.toLocaleString('en-US') + " CHF");
    d3.select("#return-percent").text((returnPercent > 0 ? "+" : "-") + returnPercent.toFixed(2) + "%");
    d3.select("#return-gain").text((returnGain > 0 ? "+" : "-") + returnGain.toLocaleString('en-US') + " CHF");
});


d3.csv("data/portfolio.csv").then(data => {
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

    function generateTable(data) {
        // Get the table body element
        const tableBody = d3.select("#portfolio-table tbody");
        
        // Clear out the previous table rows
        tableBody.selectAll("tr").remove();
    
        // Append rows to the table for each data entry matching the date
        data.forEach(d => {
            if (d.weights > 0) {
                const row = tableBody.append("tr");
    
                // Append cells for each desired column
                row.append("td").text(d.ticker);
                row.append("td").text((d.position === "long" ? "+" : "-") + (d.weights * 0.3).toFixed(2));
                row.append("td").text((d.position === "long" ? "+" : "") + d.holding_size.toFixed(2));
                row.append("td").text(d.holding_value.toLocaleString('en-US'));
                row.append("td").text(d.Close.toLocaleString('en-US'));
            }
        });
    }
    
    function updateVisualization(data) {
        // Update the table:
        generateTable(data)
    
        // Update the pie charts:
        const longDataFiltered = data.filter(d => d.position === "long" && d.weights > 0);
        const shortDataFiltered = data.filter(d => d.position === "short" && d.weights > 0);
        drawPieChart(longDataFiltered, "pie-long", 200);
        drawPieChart(shortDataFiltered, "pie-short", 150);
    }

    // const latestDate = allDates[allDates.length - 1];
    // d3.select("#selected-date").text(latestDate);
    // const filteredData = data.filter(d => +d.Date === +date);
    // updateVisualization(filteredData);

    updateVisualization(recentData);
    // Drawing pie charts
    //drawPieChart(longData, "pie-long", 200);    // Assuming radius 150 for the long pie
    //drawPieChart(shortData, "pie-short", 150);   // Half the size for the short pie
});