<?xml version='1.0' encoding='UTF-8'?>
<Project Type="Project" LVVersion="26008000">
	<Item Name="My Computer" Type="My Computer">
		<Property Name="specify.custom.address" Type="Bool">false</Property>
		<Item Name="Typedefs" Type="Folder">
			<Item Name="Channel.ctl" Type="VI" URL="../Typedefs/Channel.ctl"/>
			<Item Name="DAQ_Cmd.ctl" Type="VI" URL="../Typedefs/DAQ_Cmd.ctl"/>
			<Item Name="DAQ_Settings.ctl" Type="VI" URL="../Typedefs/DAQ_Settings.ctl"/>
			<Item Name="UI_State.ctl" Type="VI" URL="../Typedefs/UI_State.ctl"/>
		</Item>
		<Item Name="DAQ" Type="Folder">
			<Item Name="Ch_Apply.vi" Type="VI" URL="../DAQ/Ch_Apply.vi"/>
			<Item Name="Ch_Defaults.vi" Type="VI" URL="../DAQ/Ch_Defaults.vi"/>
			<Item Name="Ch_Merge_Values.vi" Type="VI" URL="../DAQ/Ch_Merge_Values.vi"/>
			<Item Name="DAQ_Engine.vi" Type="VI" URL="../DAQ/DAQ_Engine.vi"/>
			<Item Name="DAQ_Scale.vi" Type="VI" URL="../DAQ/DAQ_Scale.vi"/>
			<Item Name="TDMS_Make_Path.vi" Type="VI" URL="../DAQ/TDMS_Make_Path.vi"/>
			<Item Name="TDMS_Write_Log.vi" Type="VI" URL="../DAQ/TDMS_Write_Log.vi"/>
		</Item>
		<Item Name="UI" Type="Folder">
			<Item Name="UI_Draw_Buttons.vi" Type="VI" URL="../UI/UI_Draw_Buttons.vi"/>
			<Item Name="UI_Draw_Graph.vi" Type="VI" URL="../UI/UI_Draw_Graph.vi"/>
			<Item Name="UI_Draw_Tile.vi" Type="VI" URL="../UI/UI_Draw_Tile.vi"/>
			<Item Name="UI_Draw_Tiles.vi" Type="VI" URL="../UI/UI_Draw_Tiles.vi"/>
			<Item Name="UI_Graph_Series.vi" Type="VI" URL="../UI/UI_Graph_Series.vi"/>
			<Item Name="UI_Header_Layout.vi" Type="VI" URL="../UI/UI_Header_Layout.vi"/>
			<Item Name="UI_Hit_Test.vi" Type="VI" URL="../UI/UI_Hit_Test.vi"/>
			<Item Name="UI_Point_XY.vi" Type="VI" URL="../UI/UI_Point_XY.vi"/>
			<Item Name="UI_Render_Main.vi" Type="VI" URL="../UI/UI_Render_Main.vi"/>
			<Item Name="UI_Status_Text.vi" Type="VI" URL="../UI/UI_Status_Text.vi"/>
			<Item Name="UI_Tile_Hit.vi" Type="VI" URL="../UI/UI_Tile_Hit.vi"/>
		</Item>
		<Item Name="Dialogs" Type="Folder">
			<Item Name="Dlg_Channel.vi" Type="VI" URL="../Dialogs/Dlg_Channel.vi"/>
			<Item Name="Dlg_Graph.vi" Type="VI" URL="../Dialogs/Dlg_Graph.vi"/>
			<Item Name="Dlg_Settings.vi" Type="VI" URL="../Dialogs/Dlg_Settings.vi"/>
		</Item>
		<Item Name="Tests" Type="Folder">
			<Item Name="Test_Engine.vi" Type="VI" URL="../Tests/Test_Engine.vi"/>
			<Item Name="Test_Render.vi" Type="VI" URL="../Tests/Test_Render.vi"/>
		</Item>
		<Item Name="AI_DAQ_Main.vi" Type="VI" URL="../AI_DAQ_Main.vi"/>
		<Item Name="Dependencies" Type="Dependencies"/>
		<Item Name="Build Specifications" Type="Build"/>
	</Item>
</Project>
