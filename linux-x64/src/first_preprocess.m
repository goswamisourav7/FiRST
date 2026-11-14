mtex_path = getenv('MTEX_PATH');

if ~isempty(mtex_path)
    run(fullfile(mtex_path, 'startup_mtex.m'));
else
    fprintf('No external MTEX path provided. Assuming global configuration...\n');
end

fname = getenv('ANG_FILE_PATH');

if isempty(fname)
    error('ANG_FILE_PATH environment variable not set. Please run via the Python wrapper.');
end

setMTEXpref('showWaitbar', false);

ebsd = EBSD.load(fname, 'interface', 'ang', ...
  'convertEuler2SpatialReferenceFrame', 'setting 2');
ebsd.how2plot = plottingConvention(-zvector, xvector);

phaseNames = ebsd.mineralList;
phaseNames(strcmpi(phaseNames, 'notIndexed') | strcmpi(phaseNames, '')) = [];

fcc_phase = '';
for i = 1:length(phaseNames)
    pName = phaseNames{i};
    mineral = ebsd(pName).CS.mineral;
    
    search_str = lower([pName, ' ', mineral]);
    
    if contains(search_str, 'face centered cubic') || contains(search_str, 'fcc') || ...
       contains(search_str, 'austenite') || contains(search_str, 'gamma')
        fcc_phase = pName;
        break;
    end
end

if isempty(fcc_phase)
    error('No FCC phase detected in the .ang file. FFRS detection mathematically requires an FCC matrix.');
end
fprintf('[CHECK] Auto-detected FCC phase as: %s\n', fcc_phase);

[grains_all, ebsd.grainId] = calcGrains(ebsd, 'angle', 2*degree, 'minPixel', 5);

grainsFCC = grains_all(fcc_phase);
grains = smooth(grainsFCC, 5);

ori     = grains.meanOrientation;
nGrains = numel(grains);
csFCC   = ebsd(fcc_phase).CS;

gB = grains.boundary(fcc_phase, fcc_phase);
mSigma3 = CSL(3, csFCC);
isTwin  = angle(gB.misorientation, mSigma3) < 8.66*degree;
twinBoundary = gB(isTwin);

globalPairs = sort(twinBoundary.grainId, 2);
globalPairs = unique(globalPairs, 'rows');

[~, idx1] = ismember(globalPairs(:,1), grains.id);
[~, idx2] = ismember(globalPairs(:,2), grains.id);
pairs = [idx1, idx2]; 

totalGrainsAll = numel(grains_all(phaseNames)); 
totalBoundaryLength = sum(grains_all.boundary.segLength);
totalTwinLength = sum(twinBoundary.segLength);

statsTable = table(totalGrainsAll, totalBoundaryLength, totalTwinLength, ...
    'VariableNames', {'TotalGrains', 'TotalBoundaryLength', 'TotalTwinLength'});
writetable(statsTable, 'dataset_stats.csv');

[uniquePairs, ~, ic] = unique(sort(twinBoundary.grainId, 2), 'rows');
pairLengths = accumarray(ic, twinBoundary.segLength);

twinLenTable = table(uniquePairs(:,1), uniquePairs(:,2), pairLengths, ...
    'VariableNames', {'Grain1', 'Grain2', 'BoundaryLength'});
writetable(twinLenTable, 'twin_boundary_lengths.csv');

sigma3NeighborCount = zeros(nGrains,1);
hasTwin = false(nGrains,1);

for i = 1:size(pairs,1)
    g1 = pairs(i,1);
    g2 = pairs(i,2);
    sigma3NeighborCount(g1) = sigma3NeighborCount(g1) + 1;
    sigma3NeighborCount(g2) = sigma3NeighborCount(g2) + 1;
    hasTwin(g1) = true;
    hasTwin(g2) = true;
end

q = quaternion(ori);
grainQuat = [q.a, q.b, q.c, q.d];

h110_crystal = Miller({1,1,0}, {1,-1,0}, {1,0,1}, {1,0,-1}, {0,1,1}, {0,1,-1}, csFCC, 'hkl');
nPoles = length(h110_crystal);

grainMask = find(hasTwin);
nGrainsTwin = numel(grainMask);

dataToExport = zeros(nGrainsTwin * nPoles, 5);
idx = 1;

for ii = 1:nGrainsTwin
    g = grainMask(ii);
    currentOri = ori(g);
    gID = grains.id(g);

    pSpec = normalize(currentOri * h110_crystal);
    xyz   = pSpec.xyz;

    rows = idx : idx + nPoles - 1;
    dataToExport(rows,1) = gID;
    dataToExport(rows,2) = (1:nPoles)';
    dataToExport(rows,3:5) = xyz;
    idx = idx + nPoles;
end

grainTable = table( ...
    grains.id, ...
    grainQuat(:,1), grainQuat(:,2), ...
    grainQuat(:,3), grainQuat(:,4), ...
    hasTwin, sigma3NeighborCount, ...
    'VariableNames', ...
    {'grainID','q0','q1','q2','q3','hasSigma3','nSigma3Nbrs'} );

writetable(grainTable, 'grain_attributes.csv');

poleTable = array2table(dataToExport, ...
    'VariableNames', ["GrainID","PoleID","X","Y","Z"]);
writetable(poleTable, 'grains.csv');
fprintf('Grain-level exports complete.\n');

validPairMask = hasTwin(pairs(:,1)) & hasTwin(pairs(:,2));
pairs = pairs(validPairMask,:);
nPairs = size(pairs,1);

tolPole = 5 * degree;
pairPoleData = zeros(nPairs * 3, 9);
row = 1;

for i = 1:nPairs
    g1 = pairs(i,1);
    g2 = pairs(i,2);

    p1 = normalize(ori(g1) * h110_crystal);
    p2 = normalize(ori(g2) * h110_crystal);

    used2 = false(nPoles,1);
    nFound = 0;

    for a = 1:nPoles
        v1 = p1(a);
        dots = abs(dot(v1, p2));
        angs = acos(dots);

        angs(used2) = inf;
        [minAng, b] = min(angs);

        if minAng < tolPole
            v2 = p2(b);
            used2(b) = true;
            nFound = nFound + 1;
            
            pairPoleData(row,:) = [ ...
                grains.id(g1) grains.id(g2) nFound ... 
                v1.x v1.y v1.z ...
                v2.x v2.y v2.z ];
                
            row = row + 1;
            if nFound == 3
                break
            end
        end
    end
end
pairPoleData = pairPoleData(1:row-1,:);

pairHeader = [ ...
    "Grain1","Grain2","PoleID", ...
    "p1x","p1y","p1z", ...
    "p2x","p2y","p2z" ];

pairTable = array2table(pairPoleData, 'VariableNames', pairHeader);
writetable(pairTable,'grain_pairs.csv');
fprintf('Σ3 pair pole export complete.\n');

save('mtex_workspace.mat', 'ebsd', 'grains', 'grains_all', 'fcc_phase', '-v7.3');