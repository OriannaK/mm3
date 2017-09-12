clear all; clc;
close all;
warning off;

%% load data

dir_name = '/Users/Fangwei/Documents/Adder/Analysis/20170623_FS103_DnaN_YPet_glu_arg_25p_200ms_SJW103/analysis/picked/';
fnames = dir( [ dir_name '/*.mat' ]);

px_to_mu = 0.065;
t_int = 5.0;

%% extract and calculate all cell data

mother_cell_counter = 1;

for i=1:numel(fnames)
    struct_tmp = load([dir_name fnames(i).name]);
    fnames_channel = fieldnames(struct_tmp.cell_list);
    L_channles = length(fnames_channel(:,1));
  
    for j=1:L_channles
        fname_rec = fnames_channel{j,1};
        cell_temp = struct_tmp.cell_list.(fname_rec);

        length_temp = double(px_to_mu*cell_temp.lengths_w_div);


        if cell_temp.birth_label ==1 && isfield(cell_temp,'initiation_time') == 1 && cell_temp.lengths_w_div(end) < 20 && cell_temp.peak > 512 && cell_temp.peak < 2048 %only look at mother cells and only those have cell cycle information; %filter out filamentous cells

            generation_time( mother_cell_counter ) = t_int*double( cell_temp.tau ) ;

            newborn_length( mother_cell_counter ) = cell_temp.sb;
            newborn_width( mother_cell_counter ) = px_to_mu*cell_temp.widths(1);

            % dvision length = length of dividing mother cells; dvision width = width of dividing mother cells;
            division_length( mother_cell_counter ) = cell_temp.sd;
            division_width( mother_cell_counter ) = px_to_mu*cell_temp.widths(end);

            newborn_volume( mother_cell_counter ) = (newborn_length( mother_cell_counter )-newborn_width( mother_cell_counter ))*pi*(newborn_width( mother_cell_counter )/2)^2+(4/3)*pi*(newborn_width( mother_cell_counter )/2)^3;
            division_volume( mother_cell_counter ) = (division_length( mother_cell_counter )-division_width( mother_cell_counter ))*pi*(division_width( mother_cell_counter )/2)^2+(4/3)*pi*(division_width( mother_cell_counter )/2)^3;

            added_length( mother_cell_counter ) = division_length( mother_cell_counter ) - newborn_length( mother_cell_counter );

            added_volume( mother_cell_counter ) = division_volume( mother_cell_counter ) - newborn_volume( mother_cell_counter );

            cell_width( mother_cell_counter ) = px_to_mu*mean(cell_temp.widths(1:end));

            septum_position( mother_cell_counter ) = cell_temp.septum_position;

            birth_time( mother_cell_counter) = t_int*double(cell_temp.birth_time);
            division_time( mother_cell_counter) = t_int*double(cell_temp.division_time);

            growth_rate( mother_cell_counter ) = 60*log(division_volume( mother_cell_counter )/newborn_volume( mother_cell_counter ))/generation_time( mother_cell_counter );
            elongation_rate( mother_cell_counter ) = 60*log(division_length( mother_cell_counter )/newborn_length( mother_cell_counter ))/generation_time( mother_cell_counter );

            if length(length_temp)>2
            ft1 = fittype('a*x+b');
            Growth_time = t_int*double( cell_temp.times_w_div - cell_temp.times_w_div(1) );
            Growth_length = px_to_mu*cell_temp.lengths_w_div; 

            fit_temp = fit(Growth_time',log(Growth_length)',ft1);

            elongation_rate_fit( mother_cell_counter ) = 60*fit_temp.a;
            elseif length(length_temp)==2
            elongation_rate_fit( mother_cell_counter ) = 60*elongation_rate( mother_cell_counter );
            end

            initiation_time( mother_cell_counter ) = t_int*double(cell_temp.initiation_time);
            termination_time( mother_cell_counter ) = t_int*double(cell_temp.termination_time);

            initiation_mass( mother_cell_counter ) = cell_temp.initiation_mass;
            termination_mass( mother_cell_counter ) = cell_temp.termination_mass;

            B_period( mother_cell_counter ) = t_int*double(cell_temp.initiation_time - cell_temp.birth_time_m);
            C_period( mother_cell_counter ) = t_int*double(cell_temp.termination_time - cell_temp.initiation_time);
            D_period( mother_cell_counter ) = t_int*double(cell_temp.division_time - cell_temp.termination_time);
            tau_cyc( mother_cell_counter ) = t_int*double(cell_temp.division_time - cell_temp.initiation_time);

            mother_cell_counter = mother_cell_counter + 1;

        end
      
    end
    if mod(i,10)==0
        i
    end
end

save('/Users/Fangwei/Documents/Adder/Analysis/20170623_FS103_DnaN_YPet_glu_arg_25p_200ms_SJW103/analysis/cell_cycle_stat_GUI.mat');
