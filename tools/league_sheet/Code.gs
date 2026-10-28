/**
 * NHL '94 (Genesis) league in a Google Sheet. Paste into Extensions > Apps Script with Upload.html beside it.
 *
 * After each game: save a state in RetroArch (Genesis Plus GX) on the final stats screen, then in the Sheet use
 * NHL '94 > Upload save state. The state holds the game's memory, and with it the game's own stat counters: each
 * team's block of $364 bytes (Home at $C6CE, Away at $CA32 in work RAM) with the team totals and, per roster slot,
 * goals, assists, shots, penalty minutes, checks and ice time. The players' names come from the ROM, uploaded once
 * (NHL '94 > Load rosters from ROM), so the script holds no roster data of its own.
 *
 * Tabs: Setup (teams, owners, points), Standings, Games, Skaters, Goalies, one tab per team and one per owner (all
 * rebuilt from Games and the hidden Player games after every upload), and the hidden Rosters.
 */

var TAB = { setup: 'Setup', games: 'Games', pgames: 'Player games', rosters: 'Rosters', standings: 'Standings',
            skaters: 'Skaters', goalies: 'Goalies' };
var GAME_COLS = ['Game', 'Uploaded', 'Home', 'Away', 'Home owner', 'Away owner', 'Home goals', 'Away goals', 'Result',
                 'Home shots', 'Away shots', 'Home PP', 'Away PP', 'Home PIM', 'Away PIM', 'Home faceoffs',
                 'Away faceoffs', 'Home checks', 'Away checks', 'Home attack time', 'Away attack time', 'File', 'Check',
                 'Key'];
var PG_COLS = ['Game', 'Team', 'Owner', 'Slot', 'Player', 'Number', 'Goalie', 'Goals', 'Assists', 'Shots', 'PIM',
               'Checks', 'Ice time', 'Decision'];
var ROSTER_COLS = ['Team id', 'Abbr', 'Team', 'Slot', 'Player', 'Number', 'Goalie'];

// ---------------------------------------------------------------------------------------------- reading the files
// (pure JavaScript, no Sheets services, so it can be tested outside Google)

var HOME_BLOCK = 0xC6CE, AWAY_BLOCK = 0xCA32, SLOTS = 26;

/** The 64 KB of work RAM inside a RetroArch Genesis Plus GX save state (bytes 0-255). */
function stateRam(bytes) {
  if (text(bytes, 0, 6) === '#RZIPv') {
    throw new Error('This save state is compressed. In RetroArch, turn off Settings > Saving > Save State ' +
                    'Compression, then save the state again.');
  }
  var at = -1;
  for (var i = 0; i < 64 && at < 0; i++) if (text(bytes, i, 10) === 'GENPLUS-GX') at = i;
  if (at < 0) throw new Error('This isn\'t a Genesis Plus GX save state.');
  var start = at + 16;
  if (bytes.length < start + 0x10000) throw new Error('This save state is too short.');
  return bytes.slice(start, start + 0x10000);
}

function text(bytes, at, n) {
  var s = '';
  for (var i = 0; i < n && at + i < bytes.length; i++) s += String.fromCharCode(bytes[at + i]);
  return s;
}

// The core keeps work RAM in byte-swapped pairs: a byte at address A sits at A XOR 1, so a word reads little-endian.
function ramByte(ram, a) { return ram[(a & 0xFFFF) ^ 1]; }
function ramWord(ram, a) { a &= 0xFFFF; return ram[a] | (ram[a + 1] << 8); }

function readTeam(ram, block, teamByte) {
  var b = function (off) { return ramByte(ram, block + off); };
  var w = function (off) { return ramWord(ram, block + off); };
  var players = [];
  for (var i = 0; i < SLOTS; i++) {
    players.push({ slot: i, goals: b(0xB4 + i), assists: b(0xCE + i), shots: b(0xE8 + i), pim: b(0x102 + i),
                   checks: b(0x11C + i), toi: w(0x136 + 2 * i) });
  }
  return { team: ramByte(ram, teamByte), shots: w(0x00), ppGoals: w(0x02), powerPlays: w(0x04), pim: w(0x08),
           attack: w(0x0A), goals: w(0x0C), faceoffs: w(0x0E), checks: w(0x10), players: players };
}

/** The finished game in a save state: both teams' stats, or an Error saying why it can't be used. */
function parseState(bytes, overtime) {
  var ram = stateRam(bytes);
  var period = ramWord(ram, 0xC466), clock = ramWord(ram, 0xC468);
  var home = readTeam(ram, HOME_BLOCK, 0xC6F7), away = readTeam(ram, AWAY_BLOCK, 0xCA5B);
  var tied = home.goals === away.goals;
  var over = (period === 2 && clock === 0) || (period === 3 && (clock === 0 || !tied));
  if (!over) {
    throw new Error('The game in this save state isn\'t over (period ' + (period + 1) + ', ' + Math.floor(clock / 60) +
                    ':' + ('0' + clock % 60).slice(-2) + ' left). Save the state on the final stats screen.');
  }
  if (overtime && period === 2 && tied) {
    throw new Error('This game was tied at the end of regulation and the league plays overtime: save the state ' +
                    'after overtime, on the final stats screen.');
  }
  return { home: home, away: away, overtime: period === 3 };
}

/** The teams and rosters from a Genesis NHL '94 ROM (the original game, or a league ROM built on it). */
function parseRom(bytes) {
  var be16 = function (a) { return (bytes[a] << 8) | bytes[a + 1]; };
  var be32 = function (a) { return ((bytes[a] << 24) >>> 0) + (bytes[a + 1] << 16) + (bytes[a + 2] << 8) + bytes[a + 3]; };
  var str = function (a, n) { return text(bytes, a, n).replace(/\u0000+$/, ''); };
  if (text(bytes, 0x100, 4) !== 'SEGA') throw new Error('This isn\'t a Genesis ROM (a plain .bin, not .smd).');
  var code = text(bytes, 0x180, 14);
  var count = text(bytes, 0x120, 11) === 'NHL 94: EVO' ? 64 : /GM T-50656( -|-F)3/.test(code) ? 30 : 28;
  var teams = [];
  for (var k = 0; k < count; k++) {
    var team = be32(0x30E + 4 * k);
    var playersOff = be16(team), namesOff = be16(team + 4);
    var nibbles = [bytes[team + 0x50] >> 4, bytes[team + 0x50] & 15, bytes[team + 0x51] >> 4, bytes[team + 0x51] & 15];
    var goalies = 0;
    nibbles.forEach(function (n, i) { if (n) goalies = i + 1; });   // the first players are the goalies
    var players = [], off = team + playersOff;
    for (;;) {
      var len = be16(off);
      if (!(len > 2 && len <= 40)) break;
      var number = bytes[off + len];
      players.push({ name: str(off + 2, len - 2), number: (number >> 4) * 10 + (number & 15),
                     goalie: players.length < goalies });
      off += len + 8;
    }
    var nameLen = be16(team + namesOff);
    var abbrAt = team + namesOff + nameLen, abbrLen = be16(abbrAt);
    teams.push({ id: k, name: str(team + namesOff + 2, nameLen - 2),
                 abbr: abbrLen > 2 && abbrLen < 12 ? str(abbrAt + 2, abbrLen - 2) : 'T' + k, players: players });
  }
  return teams;
}

// ---------------------------------------------------------------------------------------------- menus and uploads

function onOpen() {
  SpreadsheetApp.getUi().createMenu('NHL \'94')
    .addItem('Upload save state…', 'showUploadState')
    .addSeparator()
    .addItem('Load rosters from ROM…', 'showUploadRom')
    .addItem('Set up the league', 'setupLeague')
    .addItem('Rebuild all tabs', 'rebuildAll')
    .addItem('Delete a game…', 'deleteGame')
    .addToUi();
}

function showDialog(mode, title) {
  var t = HtmlService.createTemplateFromFile('Upload');
  t.mode = mode;
  SpreadsheetApp.getUi().showModalDialog(t.evaluate().setWidth(440).setHeight(250), title);
}
function showUploadState() { showDialog('state', 'Upload a save state'); }
function showUploadRom() { showDialog('rom', 'Load rosters from the ROM'); }

function decode(b64) {
  return Utilities.base64Decode(b64).map(function (x) { return x & 255; });
}

/** Called by the upload dialog: the ROM's teams and rosters into the hidden Rosters tab. */
function uploadRom(b64) {
  var teams = parseRom(decode(b64));
  var rows = [];
  teams.forEach(function (t) {
    t.players.forEach(function (p, i) { rows.push([t.id, t.abbr, t.name, i, p.name, p.number, p.goalie]); });
  });
  var sh = sheet(TAB.rosters, ROSTER_COLS);
  sh.getRange(2, 1, Math.max(sh.getLastRow() - 1, 1), ROSTER_COLS.length).clearContent();
  sh.getRange(2, 1, rows.length, ROSTER_COLS.length).setValues(rows);
  sh.hideSheet();
  setupLeague();
  return 'Loaded ' + teams.length + ' teams and ' + rows.length + ' players. Now fill in the Setup tab: each team ' +
         'and its owner.';
}

/** Called by the upload dialog: one finished game into Games and Player games, then every tab rebuilt. */
function uploadState(b64, fileName) {
  var lock = LockService.getDocumentLock();
  lock.waitLock(30000);
  try {
    var setup = readSetup();
    var game = parseState(decode(b64), setup.overtime);
    var rosters = readRosters();
    var sides = [game.home, game.away].map(function (s) {
      var t = rosters[s.team];
      if (!t) throw new Error('Team ' + s.team + ' isn\'t in the rosters: load the rosters from the ROM first.');
      var owner = setup.owners[t.abbr];
      if (!owner) throw new Error(t.abbr + ' isn\'t in the Setup tab: add it with its owner, then upload again.');
      return { s: s, t: t, owner: owner };
    });
    var key = [game.home.team, game.away.team, game.home.goals, game.away.goals, game.home.shots, game.away.shots,
               game.home.players.map(function (p) { return p.goals + '.' + p.toi; }).join(','),
               game.away.players.map(function (p) { return p.goals + '.' + p.toi; }).join(',')].join('|');
    var gsh = sheet(TAB.games, GAME_COLS);
    var existing = gsh.getLastRow() > 1 ? gsh.getRange(2, 1, gsh.getLastRow() - 1, GAME_COLS.length).getValues() : [];
    existing.forEach(function (r) {
      if (r[GAME_COLS.indexOf('Key')] === key) throw new Error('This game is already in (game ' + r[0] + ').');
    });
    var number = existing.reduce(function (m, r) { return Math.max(m, Number(r[0]) || 0); }, 0) + 1;
    var h = game.home, a = game.away, H = sides[0], A = sides[1];
    var result = h.goals > a.goals ? H.t.abbr + ' win' : h.goals < a.goals ? A.t.abbr + ' win' : 'Tie';
    if (game.overtime) result += ' (OT)';
    var checks = [];
    [H, A].forEach(function (x) {
      var sum = x.s.players.reduce(function (m, p, i) { return m + (x.t.players[i] && !x.t.players[i].goalie ? p.goals : 0); }, 0);
      if (sum !== x.s.goals) checks.push(x.t.abbr + ' players\' goals ' + sum + ' against ' + x.s.goals);
    });
    if (H.owner === A.owner) checks.push('both teams belong to ' + H.owner);
    gsh.appendRow([number, new Date(), H.t.abbr, A.t.abbr, H.owner, A.owner, h.goals, a.goals, result, h.shots, a.shots,
                   h.ppGoals + '/' + h.powerPlays, a.ppGoals + '/' + a.powerPlays, h.pim, a.pim, h.faceoffs, a.faceoffs,
                   h.checks, a.checks, clock(h.attack), clock(a.attack), fileName || '',
                   checks.length ? checks.join('; ') : 'ok', key]);
    var rows = [];
    [H, A].forEach(function (x, side) {
      var mine = x.s.goals, theirs = side ? h.goals : a.goals;
      var decision = mine > theirs ? 'W' : mine < theirs ? 'L' : 'T';
      var starter = -1, most = -1;
      x.s.players.forEach(function (p, i) {
        var r = x.t.players[i];
        if (r && r.goalie && p.toi > most) { most = p.toi; starter = i; }
      });
      x.s.players.forEach(function (p, i) {
        var r = x.t.players[i];
        if (!r || !(p.toi || p.goals || p.assists || p.shots || p.pim || p.checks)) return;
        rows.push([number, x.t.abbr, x.owner, i, r.name, r.number, r.goalie, p.goals, p.assists, p.shots, p.pim,
                   p.checks, p.toi, i === starter ? decision : '']);
      });
    });
    var psh = sheet(TAB.pgames, PG_COLS);
    if (rows.length) psh.getRange(psh.getLastRow() + 1, 1, rows.length, PG_COLS.length).setValues(rows);
    psh.hideSheet();
    rebuildAll();
    return 'Game ' + number + ': ' + H.t.abbr + ' ' + h.goals + ', ' + A.t.abbr + ' ' + a.goals +
           (game.overtime ? ' (OT)' : '') + ' (' + H.owner + ' against ' + A.owner + ').' +
           (checks.length ? ' Note: ' + checks.join('; ') + '.' : '');
  } finally {
    lock.releaseLock();
  }
}

function clock(seconds) { return Math.floor(seconds / 60) + ':' + ('0' + seconds % 60).slice(-2); }

// ---------------------------------------------------------------------------------------------- setup

function sheet(name, header) {
  var ss = SpreadsheetApp.getActive();
  var sh = ss.getSheetByName(name) || ss.insertSheet(name);
  if (header && sh.getLastRow() === 0) {
    sh.getRange(1, 1, 1, header.length).setValues([header]).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  return sh;
}

function setupLeague() {
  var sh = sheet(TAB.setup);
  if (sh.getLastRow() === 0) {
    sh.getRange('A1:B1').setValues([['Team', 'Owner']]).setFontWeight('bold');
    sh.getRange('D1:E5').setValues([['Setting', 'Value'], ['Points for a win', 2], ['Points for a tie', 1],
                                     ['Overtime played', 'No'], ['Games per team', 36]]);
    sh.getRange('D1:E1').setFontWeight('bold');
    sh.getRange('D7').setValue('List each team (its abbreviation, e.g. BOS) and its owner in columns A and B.');
    sh.setFrozenRows(1);
  }
  var rosters = readRosters();
  var abbrs = Object.keys(rosters).map(function (k) { return rosters[k].abbr; });
  if (abbrs.length) {
    sh.getRange('A2:A60').setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(abbrs, true).build());
  }
  sh.getRange('E4').setDataValidation(SpreadsheetApp.newDataValidation().requireValueInList(['No', 'Yes'], true).build());
  sheet(TAB.games, GAME_COLS);
  sheet(TAB.pgames, PG_COLS).hideSheet();
  SpreadsheetApp.getActive().setActiveSheet(sh);
}

function readSetup() {
  var sh = sheet(TAB.setup);
  var v = sh.getDataRange().getValues();
  var owners = {}, teams = [];
  for (var r = 1; r < v.length; r++) {
    var team = String(v[r][0] || '').trim(), owner = String(v[r][1] || '').trim();
    if (team && owner) { owners[team] = owner; teams.push(team); }
  }
  var setting = function (name, dflt) {
    for (var r = 0; r < v.length; r++) if (String(v[r][3]).trim() === name) return v[r][4];
    return dflt;
  };
  return { owners: owners, teams: teams, win: Number(setting('Points for a win', 2)),
           tie: Number(setting('Points for a tie', 1)), overtime: String(setting('Overtime played', 'No')) === 'Yes',
           games: Number(setting('Games per team', 36)) };
}

function readRosters() {
  var sh = SpreadsheetApp.getActive().getSheetByName(TAB.rosters);
  var out = {};
  if (!sh || sh.getLastRow() < 2) return out;
  sh.getRange(2, 1, sh.getLastRow() - 1, ROSTER_COLS.length).getValues().forEach(function (r) {
    var t = out[r[0]] || (out[r[0]] = { abbr: r[1], name: r[2], players: [] });
    t.players[r[3]] = { name: r[4], number: r[5], goalie: r[6] === true || r[6] === 'TRUE' };
  });
  return out;
}

function deleteGame() {
  var ui = SpreadsheetApp.getUi();
  var ans = ui.prompt('Delete a game', 'The game number (the Games tab\'s first column):', ui.ButtonSet.OK_CANCEL);
  if (ans.getSelectedButton() !== ui.Button.OK) return;
  var n = Number(ans.getResponseText());
  [TAB.games, TAB.pgames].forEach(function (name) {
    var sh = SpreadsheetApp.getActive().getSheetByName(name);
    if (!sh) return;
    for (var r = sh.getLastRow(); r >= 2; r--) if (Number(sh.getRange(r, 1).getValue()) === n) sh.deleteRow(r);
  });
  rebuildAll();
  ui.alert('Game ' + n + ' deleted.');
}

// ---------------------------------------------------------------------------------------------- the tabs

function rows(name, cols) {
  var sh = SpreadsheetApp.getActive().getSheetByName(name);
  if (!sh || sh.getLastRow() < 2) return [];
  return sh.getRange(2, 1, sh.getLastRow() - 1, cols.length).getValues().map(function (r) {
    var o = {};
    cols.forEach(function (c, i) { o[c] = r[i]; });
    return o;
  });
}

function blankRecord() { return { gp: 0, w: 0, l: 0, t: 0, gf: 0, ga: 0, sf: 0, sa: 0, ppg: 0, pp: 0 }; }
function addGame(rec, gf, ga, sf, sa, pp) {
  rec.gp++; rec.gf += gf; rec.ga += ga; rec.sf += sf; rec.sa += sa;
  if (gf > ga) rec.w++; else if (gf < ga) rec.l++; else rec.t++;
  var p = String(pp).split('/');
  rec.ppg += Number(p[0]) || 0; rec.pp += Number(p[1]) || 0;
}
function pts(rec, setup) { return rec.w * setup.win + rec.t * setup.tie; }
function pct(a, b) { return b ? Math.round(1000 * a / b) / 10 + '%' : '-'; }

/** Every results tab from Games and Player games. */
function rebuildAll() {
  var setup = readSetup();
  var games = rows(TAB.games, GAME_COLS);
  var pgames = rows(TAB.pgames, PG_COLS);
  var teamRec = {}, ownerRec = {}, vs = {}, log = {};
  setup.teams.forEach(function (t) { teamRec[t] = blankRecord(); log[t] = []; });
  games.forEach(function (g) {
    [['Home', 'Away'], ['Away', 'Home']].forEach(function (s) {
      var me = g[s[0]], them = g[s[1]], mo = g[s[0] + ' owner'], to = g[s[1] + ' owner'];
      var gf = Number(g[s[0] + ' goals']), ga = Number(g[s[1] + ' goals']);
      var sf = Number(g[s[0] + ' shots']), sa = Number(g[s[1] + ' shots']);
      addGame(teamRec[me] || (teamRec[me] = blankRecord()), gf, ga, sf, sa, g[s[0] + ' PP']);
      addGame(ownerRec[mo] || (ownerRec[mo] = blankRecord()), gf, ga, sf, sa, g[s[0] + ' PP']);
      var k = mo + '|' + to;
      addGame(vs[k] || (vs[k] = blankRecord()), gf, ga, sf, sa, g[s[0] + ' PP']);
      (log[me] || (log[me] = [])).push([g.Game, g.Uploaded, s[0] === 'Home' ? 'Home' : 'Away', them, to,
                                        gf + '-' + ga + (String(g.Result).indexOf('OT') >= 0 ? ' OT' : ''),
                                        gf > ga ? 'W' : gf < ga ? 'L' : 'T']);
    });
  });
  // players' season totals
  var skaters = {}, goalies = {};
  pgames.forEach(function (p) {
    var key = p.Team + '|' + p.Slot;
    if (p.Goalie === true || p.Goalie === 'TRUE') {
      var g = goalies[key] || (goalies[key] = { name: p.Player, team: p.Team, owner: p.Owner, gp: 0, w: 0, l: 0, t: 0, ga: 0,
                                                 sa: 0, toi: 0 });
      g.toi += Number(p['Ice time']);
      g.ga += Number(p.Goals); g.sa += Number(p.Shots);       // a goalie's goals and shots are against
      if (p.Decision) { g.gp++; g[p.Decision.toLowerCase()]++; }
    } else {
      var s = skaters[key] || (skaters[key] = { name: p.Player, team: p.Team, owner: p.Owner, gp: 0, g: 0, a: 0, sh: 0,
                                                 pim: 0, chk: 0, toi: 0 });
      s.gp++; s.g += Number(p.Goals); s.a += Number(p.Assists); s.sh += Number(p.Shots); s.pim += Number(p.PIM);
      s.chk += Number(p.Checks); s.toi += Number(p['Ice time']);
    }
  });
  var skaterRow = function (s) {
    return [s.name, s.team, s.owner, s.gp, s.g, s.a, s.g + s.a, s.sh, pct(s.g, s.sh), s.pim, s.chk,
            clock(Math.round(s.toi / Math.max(s.gp, 1)))];
  };
  var goalieRow = function (g) {
    return [g.name, g.team, g.owner, g.gp, g.w, g.l, g.t, g.sa, g.ga, g.sa ? (1 - g.ga / g.sa).toFixed(3) : '-',
            g.gp ? (g.ga / g.gp).toFixed(2) : '-'];
  };
  var SK = ['Player', 'Team', 'Owner', 'GP', 'G', 'A', 'Pts', 'Shots', 'Sh%', 'PIM', 'Checks', 'TOI/GP'];
  var GO = ['Goalie', 'Team', 'Owner', 'GP', 'W', 'L', 'T', 'Shots against', 'GA', 'Sv%', 'GA/GP'];
  var bySkater = function (x, y) { return (y.g + y.a) - (x.g + x.a) || y.g - x.g || x.gp - y.gp; };
  var skList = Object.keys(skaters).map(function (k) { return skaters[k]; }).sort(bySkater);
  var goList = Object.keys(goalies).map(function (k) { return goalies[k]; })
    .filter(function (g) { return g.gp; }).sort(function (x, y) { return y.w - x.w || x.ga / Math.max(x.sa, 1) - y.ga / Math.max(y.sa, 1); });
  // standings
  var ST = ['Team', 'Owner', 'GP', 'W', 'L', 'T', 'Pts', 'GF', 'GA', 'Diff', 'Shots for', 'Shots against', 'PP',
            'Games left'];
  var standRow = function (t) {
    var r = teamRec[t];
    return [t, setup.owners[t] || '', r.gp, r.w, r.l, r.t, pts(r, setup), r.gf, r.ga, r.gf - r.ga, r.sf, r.sa,
            r.ppg + '/' + r.pp + ' (' + pct(r.ppg, r.pp) + ')', Math.max(setup.games - r.gp, 0)];
  };
  var order = Object.keys(teamRec).sort(function (x, y) {
    var a = teamRec[x], b = teamRec[y];
    return pts(b, setup) - pts(a, setup) || b.w - a.w || (b.gf - b.ga) - (a.gf - a.ga) || b.gf - a.gf;
  });
  write(TAB.standings, [['Standings'], ST].concat(order.map(standRow)), [1, 2]);
  write(TAB.skaters, [['Skaters'], SK].concat(skList.map(skaterRow)), [1, 2]);
  write(TAB.goalies, [['Goalies'], GO].concat(goList.map(goalieRow)), [1, 2]);
  // a tab per owner
  var owners = Object.keys(setup.owners).map(function (t) { return setup.owners[t]; })
    .filter(function (o, i, a) { return a.indexOf(o) === i; });
  owners.forEach(function (o) {
    var r = ownerRec[o] || blankRecord();
    var out = [[o + ': ' + r.w + '-' + r.l + '-' + r.t + ', ' + pts(r, setup) + ' points, goals ' + r.gf + '-' + r.ga],
               [''], ['Against each owner'], ['Owner', 'GP', 'W', 'L', 'T', 'GF', 'GA']];
    var bold = [1, 3, 4];
    owners.filter(function (x) { return x !== o; }).forEach(function (x) {
      var v = vs[o + '|' + x] || blankRecord();
      out.push([x, v.gp, v.w, v.l, v.t, v.gf, v.ga]);
    });
    out.push(['']); out.push(['Teams']); bold.push(out.length); out.push(ST); bold.push(out.length);
    order.filter(function (t) { return setup.owners[t] === o; }).forEach(function (t) { out.push(standRow(t)); });
    out.push(['']); out.push(['Top skaters']); bold.push(out.length); out.push(SK); bold.push(out.length);
    skList.filter(function (s) { return s.owner === o; }).slice(0, 20).forEach(function (s) { out.push(skaterRow(s)); });
    write(o, out, bold);
  });
  // a tab per team
  Object.keys(teamRec).forEach(function (t) {
    if (!setup.owners[t]) return;
    var r = teamRec[t];
    var out = [[t + ' (' + setup.owners[t] + '): ' + r.w + '-' + r.l + '-' + r.t + ', ' + pts(r, setup) + ' points, ' +
                r.gp + ' of ' + setup.games + ' games played'], [''], ['Games'],
               ['Game', 'Uploaded', 'Home / away', 'Opponent', 'Opponent\'s owner', 'Score', 'Result']];
    var bold = [1, 3, 4];
    (log[t] || []).forEach(function (l) { out.push(l); });
    out.push(['']); out.push(['Skaters']); bold.push(out.length); out.push(SK); bold.push(out.length);
    skList.filter(function (s) { return s.team === t; }).forEach(function (s) { out.push(skaterRow(s)); });
    out.push(['']); out.push(['Goalies']); bold.push(out.length); out.push(GO); bold.push(out.length);
    goList.filter(function (g) { return g.team === t; }).forEach(function (g) { out.push(goalieRow(g)); });
    write(t, out, bold);
  });
}

/** A results tab rewritten in full (ragged rows padded); the listed rows bold. */
function write(name, data, boldRows) {
  var sh = sheet(name);
  sh.clear();
  var width = data.reduce(function (m, r) { return Math.max(m, r.length); }, 1);
  var grid = data.map(function (r) { var c = r.slice(); while (c.length < width) c.push(''); return c; });
  sh.getRange(1, 1, grid.length, width).setValues(grid);
  (boldRows || []).forEach(function (r) { sh.getRange(r, 1, 1, width).setFontWeight('bold'); });
  sh.autoResizeColumns(1, width);
}

if (typeof module !== 'undefined') module.exports = { parseState: parseState, parseRom: parseRom, stateRam: stateRam };
