import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LineChart, Line, Area, ComposedChart } from 'recharts';
import { ChevronUp, ChevronDown, Sun, Cloud, Wind, Newspaper, Settings, ArrowLeft, Thermometer, Droplet } from 'lucide-react';

// --- MOCK DATA & CONFIGURATION ---
// Using realistic names and capacities for WA gas facilities
const ALL_FACILITIES_DATA = {
    "North West Shelf": { capacity: 420, color: "#06b6d4", zone: "Pilbara" },
    "Wheatstone": { capacity: 215, color: "#ef4444", zone: "Pilbara" },
    "Macedon": { capacity: 215, color: "#10b981", zone: "Pilbara" },
    "Scarborough": { capacity: 225, color: "#f59e0b", zone: "Pilbara" },
    "Devil Creek": { capacity: 220, color: "#8b5cf6", zone: "Pilbara" },
    "Varanus Island": { capacity: 390, color: "#3b82f6", zone: "Pilbara" },
    "Tubridgi": { capacity: 60, color: "#ec4899", zone: "Storage" },
    "Mondarra": { capacity: 150, color: "#d946ef", zone: "Storage" },
    "Other Production": { capacity: 50, color: "#6b7280", zone: "Other" }
};

const ZONES = ["Pilbara", "Storage", "Other"];

// Generate mock historical demand data for the last 2 years
const generateDemandData = (yaraAdjustment = 0) => {
    const data = [];
    const today = new Date();
    for (let i = 730; i >= 0; i--) {
        const date = new Date(today);
        date.setDate(today.getDate() - i);
        const timestamp = date.getTime();
        
        // Create seasonality and some noise
        const dayOfYear = (date.getTime() - new Date(date.getFullYear(), 0, 0).getTime()) / (1000 * 60 * 60 * 24);
        const seasonality = Math.sin((dayOfYear / 365.25) * 2 * Math.PI - Math.PI / 2); // Winter peak
        const baseDemand = 1050 + seasonality * 150;
        const noise = (Math.random() - 0.5) * 100;
        const totalDemand = baseDemand + noise + yaraAdjustment;
        
        const medianOffset = 40 + Math.random() * 10;
        
        const prevYearDate = new Date(date);
        prevYearDate.setFullYear(date.getFullYear() - 1);
        const prevYearDemand = 1020 + Math.sin((dayOfYear / 365.25) * 2 * Math.PI - Math.PI / 2) * 130 + (Math.random() - 0.5) * 80;

        data.push({
            date: date.toLocaleDateString('en-CA'), // YYYY-MM-DD for sorting
            timestamp,
            totalDemand,
            demandMedianRange: [totalDemand - medianOffset, totalDemand + medianOffset],
            lastYearDemand: prevYearDemand,
        });
    }
    return data;
};

// Generate mock supply data based on active facilities
const generateSupplyData = (demandData, activeFacilities) => {
    return demandData.map(d => {
        let cumulativeSupply = 0;
        const supplyBreakdown = {};
        
        Object.keys(activeFacilities).forEach(facility => {
            if (activeFacilities[facility]) {
                const facilityInfo = ALL_FACILITIES_DATA[facility];
                // Simulate some production variability
                const production = facilityInfo.capacity * (0.9 + Math.random() * 0.1);
                supplyBreakdown[facility] = production;
                cumulativeSupply += production;
            }
        });

        return {
            ...d,
            ...supplyBreakdown,
            totalSupply: cumulativeSupply,
        };
    });
};

// Mock data for Medium Term Capacity Chart
const facilityConstraintsData = [
    { facility: 'NW Shelf', status: 'Normal', start: '2025-01-01', end: '2027-12-31', task: 'NW Shelf Normal' },
    { facility: 'NW Shelf', status: 'Maintenance', start: '2025-09-01', end: '2025-10-15', task: 'NW Shelf Maintenance' },
    { facility: 'Wheatstone', status: 'Normal', start: '2025-01-01', end: '2027-12-31', task: 'Wheatstone Normal' },
    { facility: 'Macedon', status: 'Normal', start: '2025-01-01', end: '2027-12-31', task: 'Macedon Normal' },
    { facility: 'Macedon', status: 'Maintenance', start: '2025-10-20', end: '2025-11-30', task: 'Macedon Maintenance' },
    { facility: 'Scarborough', status: 'Construction', start: '2025-01-01', end: '2026-06-30', task: 'Scarborough Construction' },
    { facility: 'Scarborough', status: 'Normal', start: '2026-07-01', end: '2027-12-31', task: 'Scarborough Normal' },
    { facility: 'Tubridgi', status: 'Normal', start: '2025-01-01', end: '2027-12-31', task: 'Tubridgi Normal' },
    { facility: 'Mondarra', status: 'Normal', start: '2025-01-01', end: '2027-12-31', task: 'Mondarra Normal' },
];

const processGanttData = (data) => {
    const facilities = [...new Set(data.map(item => item.facility))];
    const timeline = {};
    const today = new Date('2025-07-30');

    data.forEach(item => {
        const start = new Date(item.start);
        const end = new Date(item.end);
        if (!timeline[item.facility]) {
            timeline[item.facility] = [];
        }
        timeline[item.facility].push({
            x: item.task,
            y: [start.getTime(), end.getTime()],
            fillColor: item.status === 'Normal' ? '#22c55e' : item.status === 'Maintenance' ? '#f59e0b' : '#ef4444'
        });
    });

    const series = facilities.map(facility => ({
        name: facility,
        data: timeline[facility]
    }));

    const totalCapacityData = [
        { x: '2025-01-01', y: 990 }, { x: '2025-08-31', y: 990 },
        { x: '2025-09-01', y: 620 }, { x: '2025-10-15', y: 620 },
        { x: '2025-10-16', y: 810 }, { x: '2025-11-30', y: 810 },
        { x: '2025-12-01', y: 990 }, { x: '2027-12-31', y: 990 }
    ];

    return { series, facilities, totalCapacityData };
};

// Mock News Feed Data
const newsData = [
    { id: 1, headline: "Woodside's Scarborough project faces fresh legal challenge", source: "Reuters", link: "#", date: "2025-07-29" },
    { id: 2, headline: "WA domestic gas prices to remain stable amid global uncertainty, says AEMO", source: "AEMO", link: "#", date: "2025-07-28" },
    { id: 3, headline: "Chevron announces successful maintenance at Wheatstone facility", source: "Chevron", link: "#", date: "2025-07-27" },
    { id: 4, headline: "New report highlights importance of gas in WA's energy transition", source: "WA Government", link: "#", date: "2025-07-26" },
];

// Mock Weather Data
const weatherData = {
    "Perth": { temp: 18, condition: "Cloudy", icon: <Cloud className="w-8 h-8 text-gray-500" /> },
    "Karratha": { temp: 28, condition: "Sunny", icon: <Sun className="w-8 h-8 text-yellow-500" /> }
};

// --- HELPER COMPONENTS ---

const Card = ({ children, className = '' }) => (
    <div className={`bg-white rounded-xl shadow-md p-4 sm:p-6 ${className}`}>
        {children}
    </div>
);

const PageTitle = ({ children, backAction }) => (
    <div className="flex items-center mb-6">
        {backAction && (
            <button onClick={backAction} className="p-2 rounded-full hover:bg-gray-200 mr-4">
                <ArrowLeft className="w-6 h-6 text-gray-600" />
            </button>
        )}
        <h1 className="text-2xl sm:text-3xl font-bold text-gray-800">{children}</h1>
    </div>
);


// --- CHART COMPONENTS ---

function SupplyDemandChart({ data, activeFacilities }) {
    const [dateRange, setDateRange] = useState({ start: data[data.length - 90].timestamp, end: data[data.length - 1].timestamp });

    const filteredData = useMemo(() => {
        return data.filter(d => d.timestamp >= dateRange.start && d.timestamp <= dateRange.end);
    }, [data, dateRange]);

    const handleZoom = (e) => {
        // A real implementation would use a brush or more complex controls
        // This is a simplified version
        if (e) {
            const { activeTooltipIndex } = e;
            if (activeTooltipIndex !== undefined) {
                 const newStartIndex = Math.max(0, activeTooltipIndex - 15);
                 const newEndIndex = Math.min(data.length - 1, activeTooltipIndex + 15);
                 setDateRange({start: data[newStartIndex].timestamp, end: data[newEndIndex].timestamp});
            }
        }
    };
    
    const resetZoom = () => {
        setDateRange({ start: data[data.length - 90].timestamp, end: data[data.length - 1].timestamp });
    }

    return (
        <Card>
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center mb-4">
                <div>
                    <h2 className="text-xl font-bold text-gray-800">WA Gas Supply-Demand Balance</h2>
                    <p className="text-sm text-gray-500">Live market overview. Click and drag on chart to zoom (feature simulated).</p>
                </div>
                <button onClick={resetZoom} className="mt-2 sm:mt-0 px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700">Reset Zoom</button>
            </div>
            <div style={{ width: '100%', height: 500 }}>
                <ResponsiveContainer>
                    <ComposedChart data={filteredData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }} onClick={handleZoom}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                        <YAxis label={{ value: 'TJ/day', angle: -90, position: 'insideLeft', fill: '#6b7280' }} tick={{ fontSize: 12 }} />
                        <Tooltip
                            contentStyle={{ backgroundColor: 'rgba(255, 255, 255, 0.8)', borderRadius: '0.5rem', border: '1px solid #ccc' }}
                            formatter={(value, name) => [typeof value === 'number' ? value.toFixed(0) : value, name]}
                        />
                        <Legend />
                        
                        {/* Demand Area with Median Range */}
                        <Area type="monotone" dataKey="demandMedianRange" fill="#e5e7eb" stroke="none" name="Demand Median Range" />
                        
                        {/* Supply Bars */}
                        {Object.keys(activeFacilities).filter(f => activeFacilities[f]).map(facility => (
                            <Bar key={facility} dataKey={facility} stackId="supply" fill={ALL_FACILITIES_DATA[facility].color} name={facility} />
                        ))}
                        
                        {/* Demand Lines */}
                        <Line type="monotone" dataKey="totalDemand" stroke="#374151" strokeWidth={2} dot={false} name="Total Demand" />
                        <Line type="monotone" dataKey="lastYearDemand" stroke="#000000" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Prev. 12-Month Demand" />

                    </ComposedChart>
                </ResponsiveContainer>
            </div>
        </Card>
    );
}

function MediumTermCapacityChart() {
    const { facilities } = processGanttData(facilityConstraintsData);
    
    // This is a simplified representation. A true Gantt chart in Recharts is complex.
    // We'll use a stacked bar chart to simulate the Gantt view.
    const ganttData = [
        { name: 'NW Shelf', Maintenance: 45, Normal: 320, Construction: 0 },
        { name: 'Wheatstone', Maintenance: 0, Normal: 365, Construction: 0 },
        { name: 'Macedon', Maintenance: 41, Normal: 324, Construction: 0 },
        { name: 'Scarborough', Maintenance: 0, Normal: 184, Construction: 547 },
        { name: 'Tubridgi', Maintenance: 0, Normal: 365, Construction: 0 },
        { name: 'Mondarra', Maintenance: 0, Normal: 365, Construction: 0 },
    ];


    return (
        <Card>
            <h2 className="text-xl font-bold text-gray-800 mb-1">Medium Term Capacity Outlook (2025-2026)</h2>
            <p className="text-sm text-gray-500 mb-4">Shows planned maintenance and construction activities. (Simplified View)</p>
            <div style={{ width: '100%', height: 400 }}>
                <ResponsiveContainer>
                    <BarChart layout="vertical" data={ganttData} margin={{ top: 5, right: 30, left: 30, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" />
                        <XAxis type="number" label={{ value: 'Days in Period', position: 'insideBottom', offset: -5, fill: '#6b7280' }} />
                        <YAxis type="category" dataKey="name" width={100} tick={{ fontSize: 12 }} />
                        <Tooltip formatter={(value) => `${value} days`} />
                        <Legend />
                        <Bar dataKey="Construction" stackId="a" fill="#ef4444" name="Construction" />
                        <Bar dataKey="Maintenance" stackId="a" fill="#f59e0b" name="Maintenance" />
                        <Bar dataKey="Normal" stackId="a" fill="#22c55e" name="Normal Operation" />
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </Card>
    );
}

function VolatilityChart() {
    const [dateRange, setDateRange] = useState('1Y');
    
    const generateVolatilityData = useCallback(() => {
        const data = [];
        let days;
        switch(dateRange) {
            case '1M': days = 30; break;
            case '6M': days = 180; break;
            case '1Y': days = 365; break;
            default: days = 365;
        }
        
        let value = 0.15;
        for (let i = days; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            value += (Math.random() - 0.5) * 0.05;
            value = Math.max(0.05, Math.min(0.35, value));
            data.push({ date: date.toLocaleDateString('en-CA'), volatility: value });
        }
        return data;
    }, [dateRange]);

    const volatilityData = generateVolatilityData();
    const avgVolatility = volatilityData.reduce((acc, v) => acc + v.volatility, 0) / volatilityData.length;

    return (
        <Card>
            <div className="flex justify-between items-center mb-4">
                <h3 className="font-bold text-gray-800">Historical Volatility</h3>
                <div className="flex space-x-1 bg-gray-200 rounded-lg p-1">
                    {['1M', '6M', '1Y'].map(range => (
                        <button key={range} onClick={() => setDateRange(range)} className={`px-2 py-1 text-xs font-semibold rounded-md ${dateRange === range ? 'bg-white text-blue-600 shadow' : 'text-gray-600'}`}>
                            {range}
                        </button>
                    ))}
                </div>
            </div>
            <div className="h-40">
                <ResponsiveContainer>
                    <LineChart data={volatilityData} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
                        <CartesianGrid strokeDasharray="3 3" vertical={false} />
                        <XAxis dataKey="date" tick={false} />
                        <YAxis domain={[0, 0.4]} tickFormatter={(tick) => `${(tick * 100).toFixed(0)}%`} />
                        <Tooltip formatter={(value) => `${(value * 100).toFixed(2)}%`} />
                        <Line type="monotone" dataKey="volatility" stroke="#8884d8" strokeWidth={2} dot={false} name="30d Volatility" />
                        <Line type="monotone" dataKey={() => avgVolatility} stroke="#f59e0b" strokeWidth={2} strokeDasharray="5 5" dot={false} name="Avg Volatility" />
                    </LineChart>
                </ResponsiveContainer>
            </div>
            <p className="text-center text-sm text-gray-600 mt-2">
                Average Volatility ({dateRange}): <span className="font-bold">{(avgVolatility * 100).toFixed(2)}%</span>
            </p>
        </Card>
    );
}

// --- UI & LAYOUT COMPONENTS ---

function FacilityControls({ activeFacilities, setActiveFacilities }) {
    const [isOpen, setIsOpen] = useState(false);

    const handleToggle = (facility) => {
        setActiveFacilities(prev => ({ ...prev, [facility]: !prev[facility] }));
    };

    const handleZoneToggle = (zone, value) => {
        const updatedFacilities = { ...activeFacilities };
        Object.keys(ALL_FACILITIES_DATA).forEach(facility => {
            if (ALL_FACILITIES_DATA[facility].zone === zone) {
                updatedFacilities[facility] = value;
            }
        });
        setActiveFacilities(updatedFacilities);
    };

    return (
        <div className="relative">
            <button onClick={() => setIsOpen(!isOpen)} className="w-full flex items-center justify-between px-4 py-3 bg-white rounded-xl shadow-md text-lg font-semibold text-gray-700">
                <div className="flex items-center">
                    <Settings className="w-6 h-6 mr-3 text-blue-600" />
                    <span>Manage Facilities</span>
                </div>
                {isOpen ? <ChevronUp /> : <ChevronDown />}
            </button>
            {isOpen && (
                <div className="absolute top-full left-0 right-0 mt-2 bg-white rounded-xl shadow-lg p-4 z-10">
                    <p className="text-sm text-gray-600 mb-4">Select facilities to include in the supply stack.</p>
                    {ZONES.map(zone => (
                        <div key={zone} className="mb-4">
                            <div className="flex justify-between items-center mb-2">
                                <h4 className="font-bold text-gray-700">{zone}</h4>
                                <div>
                                    <button onClick={() => handleZoneToggle(zone, true)} className="text-xs text-blue-600 hover:underline mr-2">All</button>
                                    <button onClick={() => handleZoneToggle(zone, false)} className="text-xs text-blue-600 hover:underline">None</button>
                                </div>
                            </div>
                            <div className="grid grid-cols-2 gap-2">
                                {Object.keys(ALL_FACILITIES_DATA).filter(f => ALL_FACILITIES_DATA[f].zone === zone).map(facility => (
                                    <label key={facility} className="flex items-center space-x-2 p-2 rounded-lg hover:bg-gray-100 cursor-pointer">
                                        <input
                                            type="checkbox"
                                            checked={!!activeFacilities[facility]}
                                            onChange={() => handleToggle(facility)}
                                            className="h-4 w-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                        />
                                        <span className="text-sm text-gray-800">{facility}</span>
                                    </label>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
}

function SummaryTiles({ data }) {
    const latestData = data[data.length - 1];
    const balance = latestData.totalSupply - latestData.totalDemand;
    const storageFlow = latestData['Tubridgi'] + latestData['Mondarra'] - 100; // Simplified logic

    return (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            <Card className="text-center">
                <h3 className="text-sm font-medium text-gray-500">Supply/Demand Balance</h3>
                <p className={`text-3xl font-bold ${balance > 0 ? 'text-green-600' : 'text-red-600'}`}>
                    {balance > 0 ? '+' : ''}{balance.toFixed(0)}
                </p>
                <p className="text-xs text-gray-400">TJ/day</p>
            </Card>
            <Card className="text-center">
                <h3 className="text-sm font-medium text-gray-500">Storage Flow</h3>
                <p className={`text-3xl font-bold ${storageFlow > 0 ? 'text-blue-600' : 'text-purple-600'}`}>
                    {storageFlow.toFixed(0)}
                </p>
                <p className="text-xs text-gray-400">{storageFlow > 0 ? 'Net Injection' : 'Net Withdrawal'}</p>
            </Card>
            <Card>
                <div className="flex items-center justify-center space-x-4">
                    {weatherData.Perth.icon}
                    <div>
                        <h3 className="text-sm font-medium text-gray-500">Perth</h3>
                        <p className="text-2xl font-bold text-gray-800">{weatherData.Perth.temp}°C</p>
                    </div>
                </div>
            </Card>
            <Card>
                <div className="flex items-center justify-center space-x-4">
                    {weatherData.Karratha.icon}
                    <div>
                        <h3 className="text-sm font-medium text-gray-500">Karratha</h3>
                        <p className="text-2xl font-bold text-gray-800">{weatherData.Karratha.temp}°C</p>
                    </div>
                </div>
            </Card>
        </div>
    );
}

function NewsFeed() {
    return (
        <Card>
            <div className="flex items-center mb-4">
                <Newspaper className="w-6 h-6 mr-3 text-blue-600" />
                <h2 className="text-xl font-bold text-gray-800">Live News Feed</h2>
            </div>
            <div className="space-y-4">
                {newsData.map(item => (
                    <div key={item.id}>
                        <a href={item.link} target="_blank" rel="noopener noreferrer" className="font-semibold text-gray-800 hover:text-blue-600 transition-colors">
                            {item.headline}
                        </a>
                        <div className="flex justify-between text-xs text-gray-500 mt-1">
                            <span>{item.source}</span>
                            <span>{item.date}</span>
                        </div>
                    </div>
                ))}
            </div>
        </Card>
    );
}


// --- PAGE COMPONENTS ---

function DashboardPage({ fullData, activeFacilities, setActiveFacilities, navigateTo }) {
    return (
        <div className="space-y-6">
            <SummaryTiles data={fullData} />
            <FacilityControls activeFacilities={activeFacilities} setActiveFacilities={setActiveFacilities} />
            <SupplyDemandChart data={fullData} activeFacilities={activeFacilities} />
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <MediumTermCapacityChart />
                <VolatilityChart />
            </div>
             <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <NewsFeed />
                <Card className="flex flex-col items-center justify-center text-center">
                    <h2 className="text-xl font-bold text-gray-800">Yara Pilbara Impact</h2>
                    <p className="text-sm text-gray-600 my-2">Model the market impact of changes in Yara's gas consumption.</p>
                    <button onClick={() => navigateTo('yara')} className="px-6 py-2 font-semibold text-white bg-green-600 rounded-lg hover:bg-green-700">
                        Open Scenario Planner
                    </button>
                </Card>
            </div>
        </div>
    );
}

function YaraPage({ yaraAdjustment, setYaraAdjustment, navigateTo }) {
    const [localAdjustment, setLocalAdjustment] = useState(yaraAdjustment);
    
    const historicalYaraData = useMemo(() => {
        const data = [];
        for (let i = 365; i >= 0; i--) {
            const date = new Date();
            date.setDate(date.getDate() - i);
            const usage = 85 + (Math.sin(i / 50) * 10) + (Math.random() - 0.5) * 5;
            data.push({ date: date.toLocaleDateString('en-CA'), usage: usage });
        }
        return data;
    }, []);

    const handleApply = () => {
        setYaraAdjustment(localAdjustment);
        navigateTo('dashboard');
    };

    return (
        <div>
            <PageTitle backAction={() => navigateTo('dashboard')}>Yara Pilbara Scenario Planner</PageTitle>
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                <Card className="lg:col-span-2">
                    <h2 className="text-xl font-bold text-gray-800 mb-1">Historical Gas Usage</h2>
                    <p className="text-sm text-gray-500 mb-4">Past 12 months of consumption data for Yara Pilbara.</p>
                    <div className="h-96">
                        <ResponsiveContainer>
                            <LineChart data={historicalYaraData} margin={{ top: 5, right: 20, left: -10, bottom: 5 }}>
                                <CartesianGrid strokeDasharray="3 3" />
                                <XAxis dataKey="date" tick={{ fontSize: 12 }} />
                                <YAxis label={{ value: 'TJ/day', angle: -90, position: 'insideLeft', fill: '#6b7280' }} />
                                <Tooltip formatter={(value) => `${value.toFixed(1)} TJ/day`} />
                                <Line type="monotone" dataKey="usage" stroke="#16a34a" strokeWidth={2} dot={false} name="Yara Usage" />
                            </LineChart>
                        </ResponsiveContainer>
                    </div>
                </Card>

                <Card className="flex flex-col justify-center">
                    <h2 className="text-xl font-bold text-gray-800 text-center mb-4">Adjust Market Demand</h2>
                    <p className="text-sm text-gray-600 text-center mb-6">
                        Increase or reduce Yara's assumed consumption to see its effect on the overall WA gas market balance.
                    </p>
                    <div className="flex items-center justify-center space-x-4 mb-4">
                        <button onClick={() => setLocalAdjustment(v => v - 10)} className="w-12 h-12 rounded-full bg-gray-200 text-2xl font-bold text-gray-700 hover:bg-gray-300">-</button>
                        <div className="text-center">
                            <p className={`text-4xl font-bold ${localAdjustment > 0 ? 'text-red-500' : localAdjustment < 0 ? 'text-green-500' : 'text-gray-800'}`}>
                                {localAdjustment >= 0 ? '+' : ''}{localAdjustment}
                            </p>
                            <p className="text-sm text-gray-500">TJ/day</p>
                        </div>
                        <button onClick={() => setLocalAdjustment(v => v + 10)} className="w-12 h-12 rounded-full bg-gray-200 text-2xl font-bold text-gray-700 hover:bg-gray-300">+</button>
                    </div>
                    <p className="text-xs text-center text-gray-500 mb-6">This value will be added to the total market demand.</p>
                    <button onClick={handleApply} className="w-full py-3 font-semibold text-white bg-blue-600 rounded-lg hover:bg-blue-700">
                        Apply Scenario & View Dashboard
                    </button>
                </Card>
            </div>
        </div>
    );
}

// --- MAIN APP COMPONENT ---

export default function App() {
    const [page, setPage] = useState('dashboard'); // 'dashboard' or 'yara'
    const [yaraAdjustment, setYaraAdjustment] = useState(0);

    const [activeFacilities, setActiveFacilities] = useState(() => {
        const initialState = {};
        // Set defaults as requested
        const defaultOn = ["Macedon", "Scarborough", "Devil Creek", "North West Shelf", "Wheatstone"];
        Object.keys(ALL_FACILITIES_DATA).forEach(f => {
            initialState[f] = defaultOn.includes(f);
        });
        return initialState;
    });

    // Memoize data generation to avoid recalculating on every render
    const demandData = useMemo(() => generateDemandData(yaraAdjustment), [yaraAdjustment]);
    const fullData = useMemo(() => generateSupplyData(demandData, activeFacilities), [demandData, activeFacilities]);

    const navigateTo = (targetPage) => setPage(targetPage);

    return (
        <div className="bg-gray-100 min-h-screen font-sans">
            <header className="bg-white shadow-sm">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
                    <h1 className="text-3xl font-bold text-gray-900">WA Gas Dashboard</h1>
                    <p className="text-sm text-gray-500">An interactive overview of the Western Australian gas market.</p>
                </div>
            </header>
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
                {page === 'dashboard' && (
                    <DashboardPage 
                        fullData={fullData} 
                        activeFacilities={activeFacilities}
                        setActiveFacilities={setActiveFacilities}
                        navigateTo={navigateTo}
                    />
                )}
                {page === 'yara' && (
                    <YaraPage 
                        yaraAdjustment={yaraAdjustment}
                        setYaraAdjustment={setYaraAdjustment}
                        navigateTo={navigateTo}
                    />
                )}
            </main>
            <footer className="text-center py-4">
                <p className="text-xs text-gray-500">Dashboard data is simulated for demonstration purposes. Last updated: {new Date().toLocaleDateString()}.</p>
            </footer>
        </div>
    );
}


