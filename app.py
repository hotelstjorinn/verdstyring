import { useState } from "react";
import { base44 } from "@/api/base44Client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { LogOut, Plus, Download, RefreshCw } from "lucide-react";
import PriceTable from "../components/PriceTable";
import KPITable from "../components/KPITable";
import PricingCalendar from "../components/reports/PricingCalendar";
import DemandCurve from "../components/reports/DemandCurve";
import CompetitorPricing from "../components/reports/CompetitorPricing";
import PriceOccupancyMatrix from "../components/reports/PriceOccupancyMatrix";
import BookingPace from "../components/reports/BookingPace";
import RevenueOpportunity from "../components/reports/RevenueOpportunity";
import DisplacementAnalysis from "../components/reports/DisplacementAnalysis";
import ChannelPricing from "../components/reports/ChannelPricing";
import PriceElasticity from "../components/reports/PriceElasticity";
import AIRecommendations from "../components/reports/AIRecommendations";
import PriceOverview from "../components/reports/PriceOverview";

const API_KEY = "aa73991419msh780ae4bacd33dc3p12ac5fjsn494bf3cba6a6";
const ISL_DAGAR = { 0: "Mán", 1: "Þri", 2: "Mið", 3: "Fim", 4: "Fös", 5: "Lau", 6: "Sun" };

const ROOM_CATEGORIES = [
  { label: "Suite", keywords: ["suite", "svíta"] },
  { label: "Junior Suite", keywords: ["junior suite", "junior svíta", "junior"] },
  { label: "Deluxe", keywords: ["deluxe", "superior", "premium"] },
  { label: "Standard", keywords: ["standard", "classic", "comfort", "double", "twin", "single"] },
  { label: "Economy", keywords: ["economy", "budget", "basic", "cosy", "cozy"] },
];

function flokkaHerbergi(roomName) {
  const lower = (roomName || "").toLowerCase();
  // Panta á þennan máta: suite > junior suite > deluxe > standard > economy
  if (lower.includes("junior suite") || lower.includes("junior svíta")) return "Junior Suite";
  if (lower.includes("suite") || lower.includes("svíta")) return "Suite";
  if (lower.includes("deluxe") || lower.includes("superior") || lower.includes("premium")) return "Deluxe";
  if (lower.includes("economy") || lower.includes("budget") || lower.includes("basic") || lower.includes("cosy") || lower.includes("cozy")) return "Economy";
  if (lower.includes("standard") || lower.includes("classic") || lower.includes("comfort") || lower.includes("double") || lower.includes("twin") || lower.includes("single")) return "Standard";
  return null; // Sleppa ef engin flokkun
}

function formatDate(d) {
  return `${String(d.getDate()).padStart(2, "0")}.${String(d.getMonth() + 1).padStart(2, "0")}`;
}
function addDays(d, n) {
  const r = new Date(d); r.setDate(r.getDate() + n); return r;
}
function toISO(d) {
  return d.toISOString().split("T")[0];
}

export default function Dashboard({ settings, onLogout, onResetSetup }) {
  const [gogn, setGogn] = useState([]);
  const [seldHerbergi, setSeldHerbergi] = useState([]);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [debugLog, setDebugLog] = useState([]);
  const [nyKeppinautur, setNyKeppinautur] = useState("");
  const [nyKeppHerb, setNyKeppHerb] = useState(20);
  const [localSettings, setLocalSettings] = useState(settings);
  const [valdir, setValdir] = useState([]);

  const keppinautar = localSettings?.keppinautar || {};

  async function saekjaGogn(fjoldiDaga) {
    setLoading(true);
    setGogn([]);
    setDebugLog([]);
    const logLines = [];
    const addLog = (msg) => { logLines.push(msg); setDebugLog([...logLines]); };
    const headers = {
      "X-RapidAPI-Key": API_KEY,
      "X-RapidAPI-Host": "apidojo-booking-v1.p.rapidapi.com"
    };
    const idag = new Date();
    const allHotels = {
      [localSettings.mitt_hotel_nafn]: { fjoldi: localSettings.mitt_hotel_herb },
      ...keppinautar
    };
    const nidurstodur = [];

    for (const [hotel, upplysingar] of Object.entries(allHotels)) {
      setStatus(`📡 Sæki gögn fyrir ${hotel}...`);
      const fjoldi = upplysingar?.fjoldi || 20;
      try {
        addLog(`🔍 Leita að: ${hotel}`);
        const locRes = await fetch(
          `https://apidojo-booking-v1.p.rapidapi.com/locations/auto-complete?text=${encodeURIComponent(hotel)}&languagecode=is`,
          { headers }
        );
        const locData = await locRes.json();
        addLog(`📍 ${hotel}: ${JSON.stringify(locData?.[0] || 'ekkert')}`);
        if (!locData?.length) { addLog(`⚠️ Engar leitarniðurstöður fyrir ${hotel}`); continue; }
        const destId = locData[0]?.dest_id;
        const searchType = locData[0]?.dest_type;
        addLog(`🏨 dest_id=${destId}, dest_type=${searchType}`);

        for (let i = 0; i < fjoldiDaga; i++) {
          const checkin = addDays(idag, i);
          const checkout = addDays(idag, i + 1);

          if (searchType === "hotel") {
            const roomsRes = await fetch(
              `https://apidojo-booking-v1.p.rapidapi.com/properties/v2/get-rooms?hotel_id=${destId}&arrival_date=${toISO(checkin)}&departure_date=${toISO(checkout)}&rec_guest_qty=2&currency_code=ISK`,
              { headers }
            );
            const roomsRaw = await roomsRes.json();
            addLog(`🛏️ ${hotel} ${formatDate(checkin)}: ${JSON.stringify(roomsRaw)?.substring(0, 150)}`);

            // API getur skilað array eða object með rooms sem object (key=room_id)
            let roomsList = [];
            if (Array.isArray(roomsRaw)) {
              roomsList = roomsRaw;
            } else if (roomsRaw?.rooms && typeof roomsRaw.rooms === 'object') {
              roomsList = Object.values(roomsRaw.rooms);
            }

            for (const r of roomsList) {
              // room_name getur verið á mismunandi stöðum
              const rName = r?.room_name || r?.name || r?.description || "";
              const flokkur = flokkaHerbergi(rName);
              
              // Reyna að finna lægsta verð úr block array
              const blocks = r?.block || [];
              let laegstaVerd = null;
              for (const b of blocks) {
                const price = b?.product_price_breakdown?.gross_amount?.value
                  || b?.price?.gross?.value
                  || b?.min_price?.value;
                if (price && (laegstaVerd === null || price < laegstaVerd)) {
                  laegstaVerd = price;
                }
              }

              // Ef engin flokkun en verð finns, nota 'Standard' sem default
              const finalFlokkur = flokkur || (laegstaVerd ? 'Standard' : null);
              if (!finalFlokkur || !laegstaVerd) continue;

              const exists = nidurstodur.find((x) => x.hotel === hotel && x.dagsetning === formatDate(checkin) && x.herbergjaflokkur === finalFlokkur);
              if (!exists) {
                nidurstodur.push({
                  dagsetning: formatDate(checkin),
                  dagsetning_obj: checkin,
                  vikudagur: ISL_DAGAR[checkin.getDay()],
                  hotel,
                  herbergjaflokkur: finalFlokkur,
                  verd: Math.round(laegstaVerd),
                  fjoldi_herbergja: fjoldi
                });
              }
            }

            // Ef rooms er tómt - reyna block á top-level (sum API svör)
            if (roomsList.length === 0) {
              const topBlocks = Array.isArray(roomsRaw) ? [] : (roomsRaw?.block || []);
              for (const b of topBlocks) {
                const rName = b?.room_name || b?.name || "";
                const flokkur = flokkaHerbergi(rName) || 'Standard';
                const price = b?.product_price_breakdown?.gross_amount?.value || b?.price?.gross?.value;
                if (!price) continue;
                const exists = nidurstodur.find((x) => x.hotel === hotel && x.dagsetning === formatDate(checkin) && x.herbergjaflokkur === flokkur);
                if (!exists) {
                  nidurstodur.push({
                    dagsetning: formatDate(checkin),
                    dagsetning_obj: checkin,
                    vikudagur: ISL_DAGAR[checkin.getDay()],
                    hotel,
                    herbergjaflokkur: flokkur,
                    verd: Math.round(price),
                    fjoldi_herbergja: fjoldi
                  });
                }
              }
            }
          } else {
            addLog(`⚠️ ${hotel}: dest_type er "${searchType}" - ekki "hotel"`);
          }
        }
      } catch (err) {
        addLog(`❌ Villa hjá ${hotel}: ${err.message}`);
        setStatus(`❌ Villa hjá ${hotel}: ${err.message}`);
      }
    }

    setGogn(nidurstodur);
    setSeldHerbergi(new Array(nidurstodur.length).fill(0));
    setValdir([...new Set(nidurstodur.map((r) => r.herbergjaflokkur))]);
    setStatus(nidurstodur.length > 0 ? `✅ ${nidurstodur.length} færslur sóttar!` : "⚠️ Engin gögn fundust.");
    setLoading(false);
  }

  async function baetaVidKeppinaut() {
    if (!nyKeppinautur.trim()) return;
    const updated = { ...keppinautar, [nyKeppinautur.trim()]: { fjoldi: nyKeppHerb } };
    const upd = await base44.entities.HotelSettings.update(localSettings.id, { keppinautar: updated });
    setLocalSettings({ ...localSettings, keppinautar: updated });
    setNyKeppinautur("");
    setNyKeppHerb(20);
  }

  async function fjarlaegraKeppinaut(nafn) {
    const updated = { ...keppinautar };
    delete updated[nafn];
    await base44.entities.HotelSettings.update(localSettings.id, { keppinautar: updated });
    setLocalSettings({ ...localSettings, keppinautar: updated });
  }

  // Compute KPI rows
  const mittNafn = localSettings?.mitt_hotel_nafn;
  const filteredGogn = valdir.length > 0 ? gogn.filter((r) => valdir.includes(r.herbergjaflokkur)) : gogn;
  
  const dagsetningar = [...new Set(filteredGogn.map((r) => r.dagsetning))].sort();
  const kpiRows = dagsetningar.map((dag) => {
    const dagGogn = filteredGogn.filter((r) => r.dagsetning === dag && r.verd > 0);
    const minnGogn = dagGogn.filter((r) => r.hotel === mittNafn);
    const keppGogn = dagGogn.filter((r) => r.hotel !== mittNafn);
    const mittVerd = minnGogn.length > 0 ? Math.round(minnGogn.reduce((s, r) => s + r.verd, 0) / minnGogn.length) : 0;
    const keppSumV = keppGogn.reduce((s, r) => s + r.verd * r.fjoldi_herbergja, 0);
    const keppSumH = keppGogn.reduce((s, r) => s + r.fjoldi_herbergja, 0);
    const keppAvg = keppSumH > 0 ? Math.round(keppSumV / keppSumH) : 0;
    const visitala = keppAvg > 0 ? Math.round((mittVerd / keppAvg) * 1000) / 10 : 0;
    const mismunur = mittVerd - keppAvg;
    return { dagsetning: dag, mittVerd, keppAvg, visitala, mismunur, seld: 0 };
  });

  const [kpiSeld, setKpiSeld] = useState({});
  function updateSeld(i, val) {
    setKpiSeld((prev) => ({ ...prev, [i]: val }));
  }
  const kpiRowsWithSeld = kpiRows.map((r, i) => ({ ...r, seld: kpiSeld[i] ?? 0 }));

  function sækjaCSV() {
    const rows = [["Dagsetning", "Mitt verð", "Kepp. meðaltal", "Vísitala (%)", "Mismunur", "Seld herbergi", "Nýting (%)", "RevPAR"]];
    kpiRowsWithSeld.forEach((r) => {
      const nyting = localSettings.mitt_hotel_herb > 0 ? ((r.seld / localSettings.mitt_hotel_herb) * 100).toFixed(1) : 0;
      const revpar = Math.round(r.mittVerd * nyting / 100);
      rows.push([r.dagsetning, r.mittVerd, r.keppAvg, r.visitala, r.mismunur, r.seld, nyting, revpar]);
    });
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob(["\uFEFF" + csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `Revenue_Report_${toISO(new Date())}.csv`; a.click();
  }

  const allirFlokkar = [...new Set(gogn.map((r) => r.herbergjaflokkur))];

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <div className="bg-slate-800 text-white px-6 py-4 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">📊 Hótelstjórinn</h1>
          <p className="text-slate-300 text-sm">Advanced Revenue Management System</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" className="text-slate-800 bg-white hover:bg-slate-100" onClick={onLogout}>
            <LogOut className="w-4 h-4 mr-1" /> Útskrá
          </Button>
        </div>
      </div>

      <div className="flex">
        {/* Sidebar */}
        <div className="w-72 min-h-screen bg-white border-r p-4 space-y-5 flex-shrink-0">
          <div>
            <p className="text-xs text-slate-500 uppercase font-semibold mb-1">Mitt hótel</p>
            <p className="font-bold text-slate-800">{localSettings.mitt_hotel_nafn}</p>
            <p className="text-sm text-slate-500">{localSettings.mitt_hotel_herb} herbergi</p>
            <Button variant="ghost" size="sm" className="mt-1 text-xs" onClick={onResetSetup}>Breyta</Button>
          </div>

          <Separator />

          <div>
            <p className="text-xs text-slate-500 uppercase font-semibold mb-2">Keppinautar</p>
            <div className="space-y-1 mb-3">
              {Object.entries(keppinautar).map(([nafn, v]) => (
                <div key={nafn} className="flex items-center justify-between bg-slate-50 rounded px-2 py-1">
                  <span className="text-sm">{nafn} <span className="text-slate-400">({v.fjoldi})</span></span>
                  <button onClick={() => fjarlaegraKeppinaut(nafn)} className="text-red-400 hover:text-red-600 text-xs">✕</button>
                </div>
              ))}
              {Object.keys(keppinautar).length === 0 && <p className="text-xs text-slate-400">Engir keppinautar skráðir</p>}
            </div>
            <div className="space-y-2">
              <Input placeholder="Nafn hótels" value={nyKeppinautur} onChange={(e) => setNyKeppinautur(e.target.value)} className="text-sm h-8" />
              <Input type="number" min={1} placeholder="Fjöldi herbergja" value={nyKeppHerb} onChange={(e) => setNyKeppHerb(Number(e.target.value))} className="text-sm h-8" />
              <Button size="sm" className="w-full" onClick={baetaVidKeppinaut}>
                <Plus className="w-3 h-3 mr-1" /> Bæta við
              </Button>
            </div>
          </div>

          {allirFlokkar.length > 0 && (
            <>
              <Separator />
              <div>
                <p className="text-xs text-slate-500 uppercase font-semibold mb-2">Sía herbergjaflokka</p>
                <div className="space-y-1">
                  {allirFlokkar.map((f) => (
                    <label key={f} className="flex items-center gap-2 text-sm cursor-pointer">
                      <input
                        type="checkbox"
                        checked={valdir.includes(f)}
                        onChange={(e) => {
                          if (e.target.checked) setValdir((p) => [...p, f]);
                          else setValdir((p) => p.filter((x) => x !== f));
                        }}
                      />
                      <span className="truncate">{f}</span>
                    </label>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Main content */}
        <div className="flex-1 p-6 space-y-6">
          {/* Fetch buttons */}
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base">📡 Sækja gögn frá Booking.com</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex gap-3 flex-wrap">
                <Button onClick={() => saekjaGogn(1)} disabled={loading} variant="outline">
                  <RefreshCw className="w-4 h-4 mr-1" /> Sækja í dag
                </Button>
                <Button onClick={() => saekjaGogn(7)} disabled={loading} variant="outline">
                  Sækja 7 daga
                </Button>
                <Button onClick={() => saekjaGogn(30)} disabled={loading}>
                  Sækja 30 daga
                </Button>
              </div>
              {status && <p className="mt-3 text-sm text-slate-600">{status}</p>}
              {debugLog.length > 0 && (
                <details className="mt-3">
                  <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-700 select-none">
                    🔍 Sýna {debugLog.length} skráningarlínur
                  </summary>
                  <div className="mt-2 bg-slate-900 rounded p-3 max-h-48 overflow-y-auto">
                    {debugLog.map((line, i) => (
                      <p key={i} className="text-xs text-green-300 font-mono whitespace-pre-wrap">{line}</p>
                    ))}
                  </div>
                </details>
              )}
              {loading && (
                <div className="mt-3 flex items-center gap-2 text-sm text-slate-500">
                  <div className="w-4 h-4 border-2 border-slate-300 border-t-slate-700 rounded-full animate-spin" />
                  Sæki gögn, þetta kann að taka smá stund...
                </div>
              )}
            </CardContent>
          </Card>

          <Tabs defaultValue="calendar">
            <TabsList className="flex-wrap h-auto gap-1 mb-2">
              <TabsTrigger value="overview">📊 Verðyfirlit</TabsTrigger>
              <TabsTrigger value="calendar">📅 Verðdagatal</TabsTrigger>
              <TabsTrigger value="kpi">⚙️ KPI tafla</TabsTrigger>
              <TabsTrigger value="competitor">🏨 Keppnisgreining</TabsTrigger>
              <TabsTrigger value="demand">📈 Demand Curve</TabsTrigger>
              <TabsTrigger value="elasticity">📊 Elasticity</TabsTrigger>
              <TabsTrigger value="pace">📅 Booking Pace</TabsTrigger>
              <TabsTrigger value="matrix">📉 Verð/Nýting</TabsTrigger>
              <TabsTrigger value="channel">📡 Channel</TabsTrigger>
              <TabsTrigger value="opportunity">💰 Tækifæri</TabsTrigger>
              <TabsTrigger value="displacement">🏢 Hópar</TabsTrigger>
              <TabsTrigger value="ai">🤖 AI Tillögur</TabsTrigger>
              <TabsTrigger value="raadata">📋 Gögn</TabsTrigger>
            </TabsList>

            <TabsContent value="overview">
              <Card><CardHeader className="pb-2"><CardTitle className="text-base">📊 Verðyfirlit, Meðalverð & Verðþróun</CardTitle></CardHeader>
              <CardContent><PriceOverview gogn={filteredGogn} mittNafn={mittNafn} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="calendar">
              <Card><CardHeader className="pb-2"><CardTitle className="text-base">📊 Pricing Calendar — Verðdagatal</CardTitle></CardHeader>
              <CardContent><PricingCalendar kpiRows={kpiRowsWithSeld} mittHotelHerb={localSettings.mitt_hotel_herb} onUpdateSeld={updateSeld} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="kpi">
              <Card>
                <CardHeader className="pb-3 flex flex-row items-center justify-between">
                  <CardTitle className="text-base">⚙️ KPI & Verðstefna</CardTitle>
                  <Button size="sm" variant="outline" onClick={sækjaCSV}><Download className="w-4 h-4 mr-1" /> CSV</Button>
                </CardHeader>
                <CardContent className="space-y-4">
                  <KPITable kpiRows={kpiRowsWithSeld} onUpdateSeld={updateSeld} mittHotelHerb={localSettings.mitt_hotel_herb} />
                  <div className="text-xs text-slate-500 space-y-1 bg-slate-50 p-3 rounded">
                    <p><strong>🔴 Hækka verð strax!</strong> — Nýting yfir 80% en ódýrari en markaðurinn</p>
                    <p><strong>🟢 Sterk staða</strong> — Nýting yfir 80% og á eða yfir markaðsverði</p>
                    <p><strong>🔵 Lækka verð</strong> — Nýting undir 40% og dýrari en markaðurinn</p>
                    <p><strong>🟡 Fylgjast með</strong> — Nýting og verð í jafnvægi</p>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            <TabsContent value="competitor">
              <Card><CardHeader className="pb-2"><CardTitle className="text-base">🏨 Competitor Pricing — Rate Shopping</CardTitle></CardHeader>
              <CardContent><CompetitorPricing gogn={filteredGogn} mittNafn={mittNafn} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="demand">
              <Card><CardHeader className="pb-2"><CardTitle className="text-base">📈 Demand vs Price Curve</CardTitle></CardHeader>
              <CardContent><DemandCurve kpiRows={kpiRowsWithSeld} mittHotelHerb={localSettings.mitt_hotel_herb} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="elasticity">
              <Card><CardHeader className="pb-2"><CardTitle className="text-base">📊 Price Elasticity</CardTitle></CardHeader>
              <CardContent><PriceElasticity kpiRows={kpiRowsWithSeld} mittHotelHerb={localSettings.mitt_hotel_herb} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="pace">
              <Card><CardHeader className="pb-2"><CardTitle className="text-base">📅 Booking Pace vs Price</CardTitle></CardHeader>
              <CardContent><BookingPace kpiRows={kpiRowsWithSeld} mittHotelHerb={localSettings.mitt_hotel_herb} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="matrix">
              <Card><CardHeader className="pb-2"><CardTitle className="text-base">📉 Price vs Occupancy Matrix</CardTitle></CardHeader>
              <CardContent><PriceOccupancyMatrix kpiRows={kpiRowsWithSeld} mittHotelHerb={localSettings.mitt_hotel_herb} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="channel">
              <Card><CardHeader className="pb-2"><CardTitle className="text-base">📡 Channel Pricing Performance</CardTitle></CardHeader>
              <CardContent><ChannelPricing kpiRows={kpiRowsWithSeld} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="opportunity">
              <Card><CardHeader className="pb-2"><CardTitle className="text-base">💰 Revenue Opportunity</CardTitle></CardHeader>
              <CardContent><RevenueOpportunity kpiRows={kpiRowsWithSeld} mittHotelHerb={localSettings.mitt_hotel_herb} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="displacement">
              <Card><CardHeader className="pb-2"><CardTitle className="text-base">🏢 Displacement Analysis — Hópar</CardTitle></CardHeader>
              <CardContent><DisplacementAnalysis kpiRows={kpiRowsWithSeld} mittHotelHerb={localSettings.mitt_hotel_herb} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="ai">
              <Card><CardHeader className="pb-2"><CardTitle className="text-base">🤖 AI Pricing Recommendations</CardTitle></CardHeader>
              <CardContent><AIRecommendations kpiRows={kpiRowsWithSeld} mittHotelHerb={localSettings.mitt_hotel_herb} mittNafn={mittNafn} keppinautar={keppinautar} /></CardContent></Card>
            </TabsContent>

            <TabsContent value="raadata">
              {filteredGogn.length > 0 ? (
                <Card><CardHeader className="pb-2"><CardTitle className="text-base">📋 Hrátt verðyfirlit</CardTitle></CardHeader>
                <CardContent><PriceTable df={filteredGogn} /></CardContent></Card>
              ) : <p className="text-sm text-slate-400 p-4">Engin gögn — sæktu gögn fyrst.</p>}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
