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
d3.csv("../../data/portfolios/wealth.csv").then(data => {
    const totalDeposits = data[0].wealth;

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
});
