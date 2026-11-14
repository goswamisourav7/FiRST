mtex_path = getenv('MTEX_PATH');
if ~isempty(mtex_path); run(fullfile(mtex_path, 'startup_mtex.m')); end
setMTEXpref('showWaitbar', false);
setMTEXpref('xAxisDirection', 'east');
setMTEXpref('yAxisDirection', 'south');
setMTEXpref('zAxisDirection', 'intoPlane');

if ~isfile('mtex_workspace.mat'); exit; end
load('mtex_workspace.mat');
if ~isfile('ffrs_clusters.csv'); exit; end
T = readtable('ffrs_clusters.csv');

ebsd.plottingConvention = plottingConvention(-zvector, xvector);
if ~exist('fcc_phase', 'var'); fcc_phase = 'Face Centered Cubic'; end

phaseNames = ebsd.mineralList;
phaseNames(strcmpi(phaseNames, 'notIndexed') | strcmpi(phaseNames, '')) = [];
ipfKeys = struct();

for i = 1:length(phaseNames)
    pName = phaseNames{i};
    sName = matlab.lang.makeValidName(pName);
    
    search_str = lower(pName);
    is_fcc = strcmpi(pName, fcc_phase);
    is_bcc = contains(search_str, 'body centered cubic') || contains(search_str, 'bcc') || ...
             contains(search_str, 'ferrite') || contains(search_str, 'alpha');

    if is_fcc || is_bcc
        cs_override = crystalSymmetry('m-3m', [1 1 1], 'mineral', pName);
        ipfKeys.(sName) = ipfColorKey(cs_override);
    else
        ipfKeys.(sName) = ipfColorKey(ebsd(pName).CS);
    end
    ipfKeys.(sName).inversePoleFigureDirection = zvector;
    
    fKey = figure('Visible', 'off');
    plot(ipfKeys.(sName));
    exportgraphics(fKey, sprintf('IPF_Color_Key_%s.png', sName), 'Resolution', 300);
    close(fKey);
end

csFCC = ebsd(fcc_phase).CS;
h110 = Miller(1, 1, 0, csFCC, 'hkl');
h111 = Miller(1, 1, 1, csFCC, 'hkl');
mSigma3 = CSL(3, csFCC);
mSigma9 = CSL(9, csFCC);

fA = figure('Visible', 'off');

for i = 1:length(phaseNames)
    pName = phaseNames{i};
    sName = matlab.lang.makeValidName(pName);
    ebsd_phase = ebsd(pName);
    if ~isempty(ebsd_phase)
        plot(ebsd_phase, ipfKeys.(sName).orientation2color(ebsd_phase.orientations)); 
        hold on;
    end
end

plot(grains_all.boundary, 'linecolor', 'k', 'linewidth', 0.8); 

gB_fcc = grains_all.boundary(fcc_phase, fcc_phase);
lagb_fcc = gB_fcc(gB_fcc.misorientation.angle >= 2*degree & gB_fcc.misorientation.angle < 15*degree);
plot(lagb_fcc, 'linecolor', 'w', 'linewidth', 0.4); 

margin = 5;
for i = 1:height(T)
    cID = T.ClusterID(i) + 1;
    gIDs = [T.G1(i), T.G2(i), T.G3(i), T.G4(i), T.G5(i)];
    [~, gIdx] = ismember(gIDs, grains.id);
    clusterGrains = grains(gIdx);
    
    c_x = clusterGrains.centroid.x; c_y = clusterGrains.centroid.y;
    r = clusterGrains.equivalentRadius;
    x_min = min(c_x - r) - margin; y_min = min(c_y - r) - margin;
    box_width = (max(c_x + r) + margin) - x_min;
    box_height = (max(c_y + r) + margin) - y_min;
    
    rectangle('Position', [x_min, y_min, box_width, box_height], 'EdgeColor', 'k', 'LineWidth', 2.5, 'LineStyle', '-');
    text(x_min, y_min - 2, sprintf('Cluster %d', cID), 'FontSize', 12, 'FontWeight', 'bold', 'BackgroundColor', 'w', 'EdgeColor', 'k', 'Margin', 2);
end
hold off;
exportgraphics(fA, 'Dataset_Master_Locator_Map.png', 'Resolution', 300);
close(fA);

ebsd_fcc = ebsd(fcc_phase);

for i = 1:height(T)
    cID = T.ClusterID(i) + 1;
    gIDs = [T.G1(i), T.G2(i), T.G3(i), T.G4(i), T.G5(i)];
    [~, gIdx] = ismember(gIDs, grains.id);
    clusterGrains = grains(gIdx);
    
    fC = figure('Visible', 'off');
    
    fcc_sName = matlab.lang.makeValidName(fcc_phase);
    colors_isro = ipfKeys.(fcc_sName).orientation2color(clusterGrains.meanOrientation);
    plot(clusterGrains, colors_isro, 'LineColor', 'none'); 
    hold on;
    
    plot(clusterGrains.boundary, 'linecolor', 'k', 'linewidth', 2.0);
    
    fcc_bnd = clusterGrains.boundary(fcc_phase, fcc_phase);
    is_lagb = fcc_bnd.misorientation.angle >= 2*degree & fcc_bnd.misorientation.angle < 15*degree;
    isCSL3 = angle(fcc_bnd.misorientation, mSigma3) < 8.66*degree;
    isCSL9 = angle(fcc_bnd.misorientation, mSigma9) < 5.0*degree;
    
    plot(fcc_bnd(is_lagb), 'linecolor', 'w', 'linewidth', 2.0); 
    plot(fcc_bnd(isCSL9), 'linecolor', 'g', 'linewidth', 3.0);  
    plot(fcc_bnd(isCSL3), 'linecolor', 'r', 'linewidth', 3.0);  
    
    local_margin = 3;
    xlim([min(clusterGrains.centroid.x - clusterGrains.equivalentRadius) - local_margin, max(clusterGrains.centroid.x + clusterGrains.equivalentRadius) + local_margin]);
    ylim([min(clusterGrains.centroid.y - clusterGrains.equivalentRadius) - local_margin, max(clusterGrains.centroid.y + clusterGrains.equivalentRadius) + local_margin]);
    hold off;
    exportgraphics(fC, sprintf('Cluster_%d_Fig1_Cluster_IPF.png', cID), 'Resolution', 300);
    close(fC);
    
    fD = figure('Visible', 'off');
    for j = 1:5
        g_ebsd = ebsd_fcc(clusterGrains(j));
        plotPDF(g_ebsd.orientations, h110, 'points', 'all', 'MarkerSize', 10, 'MarkerFaceColor', colors_isro(j,:), 'MarkerEdgeColor', 'k');
        hold on;
    end
    for j = 1:5
        gA = clusterGrains(j); gB = clusterGrains(mod(j, 5) + 1); 
        ax = axis(gA.meanOrientation, gB.meanOrientation);
        plot(ax, 'plane', 'color', 'r', 'lineStyle', '--', 'linewidth', 1.2);
    end
    hold off;
    exportgraphics(fD, sprintf('Cluster_%d_Fig2_Cluster_110_PF.png', cID), 'Resolution', 300);
    close(fD);

    fE = figure('Visible', 'off');
    for j = 1:5
        g_ebsd = ebsd_fcc(clusterGrains(j));
        plotPDF(g_ebsd.orientations, h111, 'points', 'all', 'MarkerSize', 10, 'MarkerFaceColor', colors_isro(j,:), 'MarkerEdgeColor', 'k');
        hold on;
    end
    hold off;
    exportgraphics(fE, sprintf('Cluster_%d_Fig3_Cluster_111_PF.png', cID), 'Resolution', 300);
    close(fE);
end

fprintf('All cluster figures generated successfully.\n');