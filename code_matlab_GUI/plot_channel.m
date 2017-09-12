function [length_list, foci_list, birth_list, division_list, cell_list, cell_names, save_name, save_name_png, display_name] = plot_channel(dir_name, cell_data, px_to_mu, IW_thr, fnames_sort, channels, channle_idx, xlim_max, ylim_max, time_int)

fov_index = find(fnames_sort(:,1) == channels(channle_idx,1));
fnames_fov = fnames_sort(fov_index,:);

channel_index = find(fnames_fov(:,2) == channels(channle_idx,2));
fnames_channel = fnames_fov(channel_index,:);

L_channles = length(fnames_channel(:,1));

foci_list = [0.0 0.0];
birth_list = 0.0;
division_list = 0.0;
cell_list = [];
cell_names = [];
length_list = [];

l_1 = 1;
i_1 = 1;
j_1 = 1;
k_1 = 1;
c_1 = 1;

for k = 1:L_channles
    fname_rec = ['f' num2str(fnames_channel(k,1),'%.2d') 'p' num2str(fnames_channel(k,2),'%.4d') 't' num2str(fnames_channel(k,3),'%.4d') 'r' num2str(fnames_channel(k,4),'%.2d')];
    cell_temp = cell_data.(fname_rec);

        if fnames_channel(k,4) ==1 && length(cell_temp.times)>=2 && isempty(cell_temp.disp_l)==0 %only look at mother cells and only those have two daughter cells and are with fluorescence

            time_temp = double(cell_temp.times); %frame number
            birth_time_temp = double(cell_temp.birth_time); %frame number
            divition_time_temp = double(cell_temp.division_time); %frame number

            length_temp = double(px_to_mu*cell_temp.lengths);
            
            length_list = [length_list [time_temp; length_temp]]; 
            
            birth_list(k_1,1) = birth_time_temp;
            k_1 = k_1+1;

            cell_list.(fname_rec) = cell_temp; %save all cells into handles' list.
            cell_names{c_1,1} = fname_rec;  %save all cells names into handles' list.
            c_1 = c_1+1;

            %-----------------plots-------------------
            % foci position vs time
            hold on;

            h1 = plot(time_temp,length_temp);
            h1.Color = [0.75 0.75 0.75]; set(h1,'LineWidth',0.5,'Markersize',2,'Marker','o','MarkerFaceColor',[0.75 0.75 0.75],'LineStyle','-');

            %obtain foci positions
            for p=1:length(cell_temp.times)
                iscell_foci = double(iscell(cell_temp.disp_l));
                if iscell_foci == 1
                    if isempty(cell_temp.disp_l{1,p})==0
                        for q=1:length(cell_temp.disp_l{1,p})
                            if cell_temp.foci_h4{1,p}(1,q)>=IW_thr
                                h3 = plot(cell_temp.times(1,p),cell_temp.disp_l{1,p}(1,q)-0.05+length_temp(1,p)/2);
                                h3.Color = [1 0 1]; set(h3,'LineWidth',1,'Markersize',2*(cell_temp.foci_h4{1,p}(1,q)/IW_thr),'Marker','o','MarkerFaceColor',[1 1 1],'LineStyle','None');

                                foci_list(i_1,:) = [double(cell_temp.times(1,p)), cell_temp.disp_l{1,p}(1,q)-0.05+length_temp(1,p)/2]; 
                                i_1 = i_1+1;

                                h4 = plot(cell_temp.times(1,p),cell_temp.disp_l{1,p}(1,q)+0.05+length_temp(1,p)/2);
                                h4.Color = [1 0 1]; set(h4,'LineWidth',1,'Markersize',2*(cell_temp.foci_h4{1,p}(1,q)/IW_thr),'Marker','o','MarkerFaceColor',[1 1 1],'LineStyle','None');

                                foci_list(i_1,:) = [double(cell_temp.times(1,p)), cell_temp.disp_l{1,p}(1,q)+0.05+length_temp(1,p)/2]; 
                                i_1 = i_1+1;
                            else
                                h3 = plot(cell_temp.times(1,p),cell_temp.disp_l{1,p}(1,q)+length_temp(1,p)/2);
                                h3.Color = [1 0 1]; set(h3,'LineWidth',1,'Markersize',2*(2*cell_temp.foci_h4{1,p}(1,q)/IW_thr),'Marker','o','MarkerFaceColor',[1 1 1],'LineStyle','None');

                                foci_list(i_1,:) = [double(cell_temp.times(1,p)), cell_temp.disp_l{1,p}(1,q)+length_temp(1,p)/2]; 
                                i_1 = i_1+1;
                            end
                        end
                    end
                end

                if iscell_foci == 0
                    for q=1:length(cell_temp.disp_l(p,1))
                        if cell_temp.foci_h4(p,q)>=IW_thr
                            h3 = plot(cell_temp.times(1,p),cell_temp.disp_l(p,q)-0.05+length_temp(1,p)/2);
                            h3.Color = [1 0 1]; set(h3,'LineWidth',1,'Markersize',2*(cell_temp.foci_h4(p,q)/IW_thr),'Marker','o','MarkerFaceColor',[1 1 1],'LineStyle','None');

                            foci_list(i_1,:) = [double(cell_temp.times(1,p)), cell_temp.disp_l(p,q)-0.05+length_temp(1,p)/2]; 
                            i_1 = i_1+1;

                            h4 = plot(cell_temp.times(1,p),cell_temp.disp_l(p,q)+0.05+length_temp(1,p)/2);
                            h4.Color = [1 0 1]; set(h4,'LineWidth',1,'Markersize',2*(cell_temp.foci_h4(p,q)/IW_thr),'Marker','o','MarkerFaceColor',[1 1 1],'LineStyle','None');

                            foci_list(i_1,:) = [double(cell_temp.times(1,p)), cell_temp.disp_l(p,q)+0.05+length_temp(1,p)/2]; 
                            i_1 = i_1+1;
                        else
                            h3 = plot(cell_temp.times(1,p),cell_temp.disp_l(p,q)+length_temp(1,p)/2);
                            h3.Color = [1 0 1]; set(h3,'LineWidth',1,'Markersize',2*(2*cell_temp.foci_h4(p,q)/IW_thr),'Marker','o','MarkerFaceColor',[1 1 1],'LineStyle','None');

                            foci_list(i_1,:) = [double(cell_temp.times(1,p)), cell_temp.disp_l(p,q)+length_temp(1,p)/2]; 
                            i_1 = i_1+1;
                        end
                    end
                end
            end

            b3 = plot(divition_time_temp*ones(1,2),[-10 10]);
            b3.Color = [0 0 0]; set(b3,'LineWidth',1,'Markersize',2,'Marker','None','MarkerFaceColor',[1 1 1],'LineStyle','--');

            division_list(j_1,1) = divition_time_temp;
            j_1 = j_1+1;
            
            b4 = plot([0 240],[0 0]); 
            b4.Color = [0 0 0]; set(b3,'LineWidth',0.5,'Markersize',2,'Marker','None','MarkerFaceColor',[1 1 1],'LineStyle','--');

            txt_tmp = sprintf('frame index (%d min/frame)',time_int);
            xlabel(txt_tmp,'fontsize',10);
            xlim([0 xlim_max])
            set(gca,'XScale','linear','XTick',[0 30 60 90 120 150 180 210 240],'XTickLabel',{'0','30','60','90','120','150','180','210','240'})

            ylabel('foci position ({\mu}m)','fontsize',10) 
            ylim([-1 ylim_max])
            set(gca,'YScale','linear','YTick',[0 1 2 3 4],'YTickLabel',{'0','1','2','3','4','5','6'},'YGrid','Off');

            set(gca,'TickLength',[0.005 0.01],'fontsize',12,'TickDir','out','PlotBoxAspectRatio',[4 1 1]);
        end

end

save_name = [dir_name 'picked/' 'f' num2str(fnames_channel(k,1),'%.2d') 'p' num2str(fnames_channel(k,2),'%.4d')];
save_name_png = [dir_name 'picked_png/' 'f' num2str(fnames_channel(k,1),'%.2d') 'p' num2str(fnames_channel(k,2),'%.4d')];
display_name = ['FOV: ' num2str(fnames_channel(1,1),'%.2d') '; Channel: ' num2str(fnames_channel(1,2),'%.4d')];

end